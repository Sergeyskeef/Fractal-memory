"""
Redis Streams хранилище для L0/L1.

Используем:
- XADD с MAXLEN для автоматического trim
- XREVRANGE для чтения (новые первые)
- SCAN вместо KEYS для итерации
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisMemoryStore:
    """Хранилище L0/L1 на Redis Streams."""
    
    def __init__(self, redis_url: str, user_id: str, max_l0_size: int = 500):
        self.redis_url = redis_url
        self.user_id = user_id
        self.max_l0_size = max_l0_size
        self.client: Optional[redis.Redis] = None
        
        # Ключи
        self.l0_stream = f"memory:{user_id}:l0:stream"
        self.l1_prefix = f"memory:{user_id}:l1:session"
        self.consolidated_set = f"memory:{user_id}:consolidated"
        self.l1_summary_list = f"memory:{user_id}:l1:summary:list"
    
    async def connect(self) -> None:
        """Подключиться к Redis."""
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        await self.client.ping()
        logger.info(f"Redis connected for user {self.user_id}")
    
    async def close(self) -> None:
        """Закрыть соединение."""
        if self.client:
            await self.client.aclose()
    
    # ==================== L0 (Working Memory) ====================
    
    async def l0_add(self, content: str, importance: float, 
                     metadata: Dict = None) -> str:
        """Добавить в L0 Stream с автоматическим trim."""
        
        data = {
            "content": content,
            "importance": str(importance),
            "timestamp": datetime.now().isoformat(),
            "metadata": json.dumps(metadata or {}),
        }
        
        # XADD с MAXLEN — автоматически удаляет старые
        stream_id = await self.client.xadd(
            self.l0_stream,
            data,
            maxlen=self.max_l0_size,
            approximate=True,  # ~ для производительности
        )
        
        return stream_id
    
    async def l0_get_recent(self, count: int = 50) -> List[Dict]:
        """Получить последние N элементов L0."""
        items = await self.client.xrevrange(self.l0_stream, count=count)
        
        return [
            {
                "stream_id": item[0],
                "content": item[1].get("content"),
                "importance": float(item[1].get("importance", 0.5)),
                "timestamp": item[1].get("timestamp"),
                "metadata": json.loads(item[1].get("metadata", "{}")),
            }
            for item in items
        ]
    
    async def l0_get_unconsolidated(self, limit: int = 100) -> List[Dict]:
        """Получить элементы, которые ещё не консолидированы."""
        all_items = await self.l0_get_recent(limit * 2)
        consolidated_ids = await self.client.smembers(self.consolidated_set)
        
        return [
            item for item in all_items
            if item["stream_id"] not in consolidated_ids
        ]
    
    async def l0_mark_consolidated(self, stream_ids: List[str]) -> None:
        """Пометить как консолидированные (idempotency)."""
        if stream_ids:
            await self.client.sadd(self.consolidated_set, *stream_ids)
            # TTL на set — очищаем старые через 7 дней
            await self.client.expire(self.consolidated_set, 7 * 24 * 3600)
    
    async def l0_count(self) -> int:
        """Количество элементов в L0."""
        return await self.client.xlen(self.l0_stream)

    async def l0_clear_buffer(self) -> None:
        """Полностью очистить буфер L0 и метки консолидации."""
        try:
            await self.client.delete(self.l0_stream)
            await self.client.delete(self.consolidated_set)
        except Exception:
            pass
    
    # ==================== L1 (Session Memory) ====================
    
    async def l1_add_session(self, session_id: str, summary: str,
                             importance: float, source_ids: List[str]) -> None:
        """Добавить сессию в L1."""
        key = f"{self.l1_prefix}:{session_id}"
        
        data = {
            "session_id": session_id,
            "summary": summary,
            "importance": str(importance),
            "source_count": str(len(source_ids)),
            "source_ids": json.dumps(source_ids),
            "created_at": datetime.now().isoformat(),
            "promoted_to_l2": "false",
        }
        
        await self.client.hset(key, mapping=data)
        # TTL 30 дней
        await self.client.expire(key, 30 * 24 * 3600)

    async def l1_add_summary_entry(self, session_id: str, summary: str, importance: float) -> None:
        """
        Добавить саммари в список L1 (для быстрого доступа последних N).
        Храним JSON строками, newest first (LPUSH).
        """
        payload = json.dumps({
            "session_id": session_id,
            "summary": summary,
            "importance": importance,
            "created_at": datetime.now().isoformat()
        })
        await self.client.lpush(self.l1_summary_list, payload)
        # Ограничиваем длину списка до 50
        await self.client.ltrim(self.l1_summary_list, 0, 49)
    
    async def l1_get_sessions(self) -> List[Dict]:
        """Получить все сессии L1 через SCAN (не KEYS!)."""
        sessions = []
        
        # SCAN с паттерном — не блокирует Redis
        async for key in self.client.scan_iter(
            match=f"{self.l1_prefix}:*",
            count=100
        ):
            data = await self.client.hgetall(key)
            if data:
                sessions.append({
                    "session_id": data.get("session_id"),
                    "summary": data.get("summary"),
                    "importance": float(data.get("importance", 0.5)),
                    "source_count": int(data.get("source_count", 0)),
                    "created_at": data.get("created_at"),
                    "promoted_to_l2": data.get("promoted_to_l2") == "true",
                })
        
        return sessions
    
    async def l1_get_recent_summaries(self, count: int = 3) -> List[Dict]:
        """Получить последние саммари L1 (из списка)."""
        items = await self.client.lrange(self.l1_summary_list, 0, count - 1)
        results: List[Dict] = []
        for raw in items:
            try:
                parsed = json.loads(raw)
                results.append(parsed)
            except Exception:
                continue
        return results
    
    async def l1_mark_promoted(self, session_id: str) -> None:
        """Пометить сессию как продвинутую в L2."""
        key = f"{self.l1_prefix}:{session_id}"
        await self.client.hset(key, "promoted_to_l2", "true")
        await self.client.hset(key, "promoted_at", datetime.now().isoformat())
    
    async def l1_get_unpromoted(self) -> List[Dict]:
        """Получить сессии, которые не продвинуты в L2."""
        sessions = await self.l1_get_sessions()
        return [s for s in sessions if not s.get("promoted_to_l2")]
    
    async def l1_count(self) -> int:
        """Количество сессий в L1."""
        count = 0
        async for _ in self.client.scan_iter(match=f"{self.l1_prefix}:*"):
            count += 1
        return count
    
    # ==================== Search ====================
    
    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Простой поиск по L0/L1 (для гибридного retrieval)."""
        results: List[Dict] = []
        query_lower = query.lower()
        
        # L0
        l0_items = await self.l0_get_recent(200)
        for item in l0_items:
            if query_lower in item.get("content", "").lower():
                item["source"] = "L0"
                results.append(item)
        
        # L1
        sessions = await self.l1_get_sessions()
        for session in sessions:
            if query_lower in session.get("summary", "").lower():
                session["source"] = "L1"
                results.append(session)
        
        # Сортировка по важности
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:limit]

    async def search_l0_l1(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск по L0 и L1 для загрузки пользовательского контекста."""
        results: List[Dict] = []
        query_lower = query.lower()

        # L0 — последние элементы из стрима
        l0_items = await self.l0_get_recent(200)
        for item in l0_items:
            content = item.get("content", "") or ""
            if query_lower in content.lower():
                results.append(
                    {
                        "content": content,
                        "level": "l0",
                        "importance": item.get("importance", 0.5),
                        "timestamp": item.get("timestamp"),
                    }
                )

        # L1 — сессионные summary
        l1_sessions = await self.l1_get_sessions()
        for session in l1_sessions:
            summary = session.get("summary", "") or ""
            if query_lower in summary.lower():
                results.append(
                    {
                        "content": summary,
                        "level": "l1",
                        "importance": session.get("importance", 0.5),
                        "timestamp": session.get("created_at"),
                    }
                )

        # Сортировка по важности, самые важные первыми
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:limit]
    
    # ==================== Stats ====================
    
    async def get_stats(self) -> Dict[str, int]:
        """Статистика."""
        return {
            "l0_count": await self.l0_count(),
            "l1_count": await self.l1_count(),
            "l1_summaries": await self.client.llen(self.l1_summary_list) if self.client else 0,
        }

