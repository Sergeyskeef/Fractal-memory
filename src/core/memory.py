"""
FractalMemory — главный класс памяти с фрактальной иерархией.

Уровни памяти:
- L0: Working Memory (Python list, секунды)
- L1: Short-Term Memory (Python dict, минуты-часы)  
- L2: Medium-Term Memory (Graph, дни)
- L3: Long-Term Memory (Graph, месяцы-годы)

Использование:
    memory = FractalMemory(config)
    await memory.initialize()
    
    # Запомнить
    await memory.remember("Пользователь любит Python")
    
    # Вспомнить
    results = await memory.recall("что любит пользователь")
    
    # Консолидация (вызывается автоматически или вручную)
    await memory.consolidate()
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncio
import logging
import uuid
import numpy as np
import re
import json

from .graphiti_store import GraphitiStore, SearchResult
from .redis_store import RedisMemoryStore
from .embeddings import OpenAIEmbedder
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# МОДЕЛИ ДЛЯ ВНУТРЕННЕГО ИСПОЛЬЗОВАНИЯ
# ═══════════════════════════════════════════════════════════

@dataclass
class MemoryItem:
    """Элемент памяти (для L0/L1)"""
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    importance: float = 1.0
    access_count: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    level: int = 0  # 0=L0, 1=L1
    metadata: Dict = field(default_factory=dict)


@dataclass 
class ConsolidationResult:
    """Результат консолидации"""
    promoted: int  # Повышено на уровень выше
    decayed: int   # Понижен importance
    deleted: int   # Удалено (soft delete)


# ═══════════════════════════════════════════════════════════
# FRACTAL MEMORY
# ═══════════════════════════════════════════════════════════

class FractalMemory:
    """
    Фрактальная память с иерархией L0 → L1 → L2 → L3.
    
    Принципы:
    1. Важное поднимается выше (консолидация)
    2. Неважное забывается (decay)
    3. Всё доступно через единый интерфейс
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: {
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "redis_url": "redis://localhost:6379",
                "user_id": "default",
                "llm_client": <optional>,
                "embedding_func": <optional callable>,
                
                # Опции памяти
                "l0_capacity": 10,
                "l1_capacity": 50,
                "decay_rate_l0": 0.1,
                "decay_rate_l1": 0.05,
                "importance_threshold": 0.3,
                "consolidation_interval": 300,  # секунды
            }
        """
        self.config = config
        self.user_id = config.get("user_id", "default")
        
        # Graphiti store (L2/L3) - новый компонент
        self.graphiti: Optional[GraphitiStore] = None
        
        # Redis store для L0/L1 (персистентное хранилище) - новый компонент
        self.redis_store: Optional[RedisMemoryStore] = None
        
        # L0: Working Memory (очень короткая)
        # In-memory кэш (копия из Redis для быстрого доступа)
        self.l0_cache: List[MemoryItem] = []
        self.l0_capacity = config.get("l0_capacity", 10)
        
        # L1: Short-Term Memory
        self.l1_cache: Dict[str, MemoryItem] = {}
        self.l1_capacity = config.get("l1_capacity", 50)
        
        # Decay rates
        self.decay_rate_l0 = config.get("decay_rate_l0", 0.1)
        self.decay_rate_l1 = config.get("decay_rate_l1", 0.05)
        self.importance_threshold = config.get("importance_threshold", 0.3)
        self.consolidation_interval = config.get("consolidation_interval", 300)
        # Новые настройки консолидации
        self.l0_consolidation_batch = config.get("l0_consolidation_batch", 15)
        self._llm_model = config.get("llm_model", "gpt-5-mini")
        self.last_episode_id: Optional[str] = None
        self._consolidation_lock = asyncio.Lock()
        self.auto_consolidate_l0 = config.get("auto_consolidate_l0", True)  # Боевой default: True
        
        # Embedding function (FIX: Auto-init OpenAIEmbedder if not provided)
        self.embedding_func = config.get("embedding_func")
        if self.embedding_func is None:
            try:
                embedder = OpenAIEmbedder()
                # Проверяем, есть ли ключ, чтобы не падать сразу, если его нет
                if embedder.client:
                    self.embedding_func = embedder.get_embedding
                    logger.info("Using default OpenAIEmbedder for embeddings")
                else:
                    logger.warning("OPENAI_API_KEY not found, embeddings will be disabled")
            except Exception as e:
                logger.warning(f"Failed to init default embedder: {e}")
        
        # State
        self._initialized = False
        self._consolidation_task = None
    
    async def initialize(self) -> None:
        """Инициализация памяти"""
        if self._initialized:
            return
        
        # Инициализировать Redis store (новый компонент)
        redis_url = self.config.get("redis_url", "redis://localhost:6379")
        max_l0_size = self.config.get("l0_max_size", 500)
        self.redis_store = RedisMemoryStore(redis_url, self.user_id, max_l0_size)
        await self.redis_store.connect()
        
        # Инициализировать Graphiti store (новый компонент)
        # Безопасность: пароль должен быть в конфиге, без дефолта
        neo4j_password = self.config.get("neo4j_password")
        if not neo4j_password:
            raise ValueError(
                "neo4j_password is required. Set it in config or NEO4J_PASSWORD environment variable."
            )
        
        self.graphiti = GraphitiStore(
            neo4j_uri=self.config.get("neo4j_uri", "bolt://localhost:7687"),
            neo4j_user=self.config.get("neo4j_user", "neo4j"),
            neo4j_password=neo4j_password,
            user_id=self.user_id
        )
        await self.graphiti.connect()
        
        # Загрузить L0/L1 из Redis
        await self._load_from_redis()
        
        self._initialized = True
        logger.info(f"FractalMemory initialized for user {self.user_id}")
        
        if (
            self.consolidation_interval
            and self.consolidation_interval > 0
            and (self._consolidation_task is None or self._consolidation_task.done())
        ):
            self._consolidation_task = asyncio.create_task(
                self._consolidation_loop()
            )
    
    async def _load_from_redis(self) -> None:
        """Загрузить L0/L1 из Redis при старте."""
        if not self.redis_store:
            return
        
        try:
            # Загрузить L0 (новый API: l0_get_recent)
            l0_items = await self.redis_store.l0_get_recent(count=100)
            self.l0_cache = []
            for item in l0_items:
                try:
                    created_at = datetime.fromisoformat(item.get("timestamp", datetime.now().isoformat()))
                except:
                    created_at = datetime.now()
                
                self.l0_cache.append(MemoryItem(
                    id=item.get("stream_id", self._generate_id()),
                    content=item.get("content", ""),
                    embedding=None,
                    importance=item.get("importance", 0.5),
                    created_at=created_at,
                    last_accessed=created_at,
                    level=0,
                    metadata=item.get("metadata", {}),
                ))
            
            # Загрузить L1 (новый API: l1_get_sessions)
            l1_sessions = await self.redis_store.l1_get_sessions()
            self.l1_cache = {}
            for session in l1_sessions:
                try:
                    created_at = datetime.fromisoformat(session.get("created_at", datetime.now().isoformat()))
                except:
                    created_at = datetime.now()
                
                # Создать MemoryItem для сессии
                self.l1_cache[session.get("session_id")] = MemoryItem(
                    id=session.get("session_id", self._generate_id()),
                    content=session.get("summary", ""),
                    embedding=None,
                    importance=session.get("importance", 0.5),
                    created_at=created_at,
                    last_accessed=created_at,
                    level=1,
                    metadata={"session_id": session.get("session_id"), "source_count": session.get("source_count", 0)},
                )
            
            logger.info(f"Loaded from Redis: L0={len(self.l0_cache)}, L1 sessions={len(self.l1_cache)}")
            
        except Exception as e:
            logger.warning(f"Failed to load from Redis: {e}")
    
    async def close(self) -> None:
        """Закрытие памяти"""
        if self._consolidation_task:
            self._consolidation_task.cancel()
            try:
                await self._consolidation_task
            except asyncio.CancelledError:
                pass
            self._consolidation_task = None
        if self.graphiti:
            await self.graphiti.close()
        if self.redis_store:
            await self.redis_store.close()
        self._initialized = False
    
    async def _consolidation_loop(self) -> None:
        """Фоновая консолидация L0 → L1 → L2"""
        try:
            while self._initialized:
                await asyncio.sleep(self.consolidation_interval)
                if not self._initialized:
                    break
                try:
                    await self.consolidate()
                except Exception as exc:
                    logger.warning(f"Auto consolidation failed: {exc}")
        except asyncio.CancelledError:
            logger.debug("Consolidation loop cancelled")
            raise
    
    # ═══════════════════════════════════════════════════════
    # ОСНОВНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════
    
    async def remember(
        self, 
        content: str,
        importance: float = 1.0,
        metadata: Dict = None
    ) -> str:
        """
        Запомнить информацию.
        Сначала в L0, потом консолидируется выше.
        
        Args:
            content: Что запомнить
            importance: Начальная важность (0-1)
            metadata: Дополнительные данные
        
        Returns:
            ID созданной записи
        """
        self._ensure_initialized()
        
        metadata = metadata or {}
        
        # Создать embedding если есть функция
        embedding = None
        if self.embedding_func:
            embedding = await self._get_embedding(content)
        
        # Создать MemoryItem
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            embedding=embedding,
            importance=importance,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            level=0,
            metadata=dict(metadata)
        )
        
        # Добавить в L0 (in-memory кэш)
        self.l0_cache.append(item)
        
        # Сохранить в Redis (персистентно) - новый API
        if self.redis_store:
            await self.redis_store.l0_add(
                content=content,
                importance=importance,
                metadata=metadata
            )
        
        logger.debug(f"Added to L0: {item.id[:8]}... (importance={importance:.2f})")
        
        # Батч-триггер консолидации: атомарный lock в Redis, чтобы исключить двойные запуски
        if self.auto_consolidate_l0 and self.redis_store:
            unconsolidated = await self.redis_store.l0_get_unconsolidated(limit=self.l0_consolidation_batch)
            if len(unconsolidated) >= self.l0_consolidation_batch:
                lock_key = f"memory:{self.user_id}:consolidation_lock"
                try:
                    # SETNX с TTL 60s — если занято, просто выходим
                    locked = await self.redis_store.client.set(lock_key, "1", nx=True, ex=60)
                except Exception as exc:
                    logger.warning(f"Redis lock check failed: {exc}")
                    locked = False
                if locked:
                    logger.info("🚀 Triggering Auto-Consolidation (lock acquired)")
                    asyncio.create_task(self._consolidate_l0_to_l1_locked_wrapper(lock_key))
                else:
                    logger.info("⚠️ Consolidation skipped (lock already active)")
        
        # Автоконсолидация L1→L2 при накоплении важных данных
        important_in_l1 = sum(
            1 for item in self.l1_cache.values()
            if item.importance >= 0.7
        )
        if important_in_l1 >= 5:  # 5+ важных записей
            logger.info(f"Auto-consolidating L1→L2: {important_in_l1} important items")
            await self._consolidate_l1_to_l2()
        
        return item.id
    
    async def recall(
        self, 
        query: str,
        limit: int = 5,
        levels: List[int] = None
    ) -> List[SearchResult]:
        """
        Вспомнить информацию.
        Ищет по всем уровням памяти.
        
        Args:
            query: Что искать
            limit: Максимум результатов
            levels: Какие уровни искать [0,1,2,3] или None для всех
        
        Returns:
            Список результатов, отсортированных по релевантности
        """
        self._ensure_initialized()
        
        if levels is None:
            levels = [0, 1, 2, 3]
        
        all_results = []
        
        # L0: поиск в working memory
        if 0 in levels:
            l0_results = self._search_l0(query)
            all_results.extend(l0_results)
        
        # L1: поиск в short-term
        if 1 in levels:
            l1_results = self._search_l1(query)
            all_results.extend(l1_results)
        
        # L2/L3: поиск в графе через GraphitiStore
        graph_results = []
        if 2 in levels or 3 in levels:
            if self.graphiti:
                graphiti_results = await self.graphiti.search(query, limit=limit * 2)
                # Преобразовать SearchResult в формат для recall
                graph_results = [
                    SearchResult(
                        content=r.content,
                        score=r.score,
                        source=r.source,
                        timestamp=datetime.now(),
                        metadata=r.metadata or {}
                    )
                    for r in graphiti_results
                ]
            all_results.extend(graph_results)
        
        # Сортировка по relevance
        all_results.sort(key=lambda x: x.score, reverse=True)
        top_results = all_results[:limit]

        # Обновить access_count для найденных
        await self._update_access_counts(top_results)

        # Обновить last_accessed в графе для L2/L3 результатов
        if graph_results:
            try:
                await self._update_graph_last_accessed(graph_results)
            except Exception as e:
                logger.warning(f"Failed to update graph last_accessed: {e}")
        
        return top_results

    async def _update_graph_last_accessed(
        self,
        results: List[SearchResult],
    ) -> None:
        """Обновить last_accessed для эпизодов в графе.

        Опираемся на то, что Graphiti при поиске возвращает в metadata
        идентификаторы эпизодов (uuid/episode_uuid/episode_name).
        """
        # Собрать все известные идентификаторы эпизодов
        episode_ids = set()
        for r in results:
            meta = r.metadata or {}
            for key in ("episode_id", "episode_uuid", "uuid", "episode_name", "name"):
                value = meta.get(key)
                if isinstance(value, str) and value:
                    episode_ids.add(value)
            
            episode_uuids = meta.get("episode_uuids")
            if isinstance(episode_uuids, list):
                for uid in episode_uuids:
                    if isinstance(uid, str) and uid:
                        episode_ids.add(uid)
            elif isinstance(episode_uuids, str) and episode_uuids:
                episode_ids.add(episode_uuids)

        if not episode_ids:
            logger.debug("No episode IDs found to update last_accessed")
            return

        try:
            if self.graphiti:
                # В Graphiti эпизоды имеют метку Episodic и поле uuid.
                await self.graphiti.execute_cypher(
                    """
                    MATCH (ep:Episodic)
                    WHERE ep.uuid IN $ids
                    SET ep.valid_at = datetime()
                    """,
                    {"ids": list(episode_ids)},
                )
                logger.debug(f"Updated valid_at for {len(episode_ids)} episodic IDs")
        except Exception as exc:
            logger.warning(f"Failed to update graph last_accessed: {exc}")
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        levels: List[int] = None
    ) -> List[SearchResult]:
        """
        Search for information in memory (alias for recall).
        
        This method provides API compatibility with expected interface.
        
        Args:
            query: Search query
            limit: Maximum number of results
            levels: Which levels to search [0,1,2,3] or None for all
        
        Returns:
            List of results sorted by relevance
        """
        return await self.recall(query=query, limit=limit, levels=levels)
    
    async def consolidate(self) -> ConsolidationResult:
        """
        Консолидация памяти: L0 → L1 → L2 → L3.
        Вызывается автоматически или вручную.
        
        Returns:
            Статистика консолидации
        """
        self._ensure_initialized()
        
        result = ConsolidationResult(promoted=0, decayed=0, deleted=0)
        
        # L0 → L1
        r1 = await self._consolidate_l0_to_l1()
        result.promoted += r1.promoted
        result.decayed += r1.decayed
        result.deleted += r1.deleted
        
        # L1 → L2
        r2 = await self._consolidate_l1_to_l2()
        result.promoted += r2.promoted
        result.decayed += r2.decayed
        result.deleted += r2.deleted
        
        # Apply decay to all levels
        await self._apply_decay()
        
        logger.info(
            f"Consolidation complete: "
            f"promoted={result.promoted}, "
            f"decayed={result.decayed}, "
            f"deleted={result.deleted}"
        )
        
        return result
    
    # ═══════════════════════════════════════════════════════
    # КОНСОЛИДАЦИЯ
    # ═══════════════════════════════════════════════════════
    
    async def _consolidate_l0_to_l1(self) -> ConsolidationResult:
        """
        Консолидация L0 → L1 через батч-саммари, без прямого спама в Graphiti.
        Триггер: объём L0 >= l0_consolidation_batch (15 по умолчанию) или ручной вызов.
        """
        result = ConsolidationResult(promoted=0, decayed=0, deleted=0)
        if not self.redis_store:
            return result
        
        # Берём неконсолидированные элементы из Redis
        l0_items = await self.redis_store.l0_get_unconsolidated(limit=self.l0_consolidation_batch)
        if len(l0_items) < self.l0_consolidation_batch:
            # Недостаточно данных для батча — выходим без изменений
            return result
        
        # Обновляем importance/фильтруем шум
        kept_items: List[MemoryItem] = []
        stream_ids: List[str] = []
        now = datetime.now()
        for raw in l0_items:
            created_at = datetime.fromisoformat(raw.get("timestamp")) if raw.get("timestamp") else now
            item = MemoryItem(
                id=raw.get("stream_id"),
                content=raw.get("content", ""),
                embedding=None,
                importance=float(raw.get("importance", 0.5)),
                created_at=created_at,
                last_accessed=created_at,
                level=0,
                metadata=raw.get("metadata", {}),
            )
            age_minutes = (now - item.created_at).total_seconds() / 60
            item.importance = self._calculate_importance(item, age_minutes)
            if item.importance < self.importance_threshold:
                result.deleted += 1
                continue
            kept_items.append(item)
            stream_ids.append(item.id)
        
        if not kept_items:
            await self.redis_store.l0_mark_consolidated(stream_ids)
            return result
        
        # Генерируем саммари батча через GPT-5 Nano (fallback — concatenate)
        summary_text = await self._summarize_batch(kept_items)
        summary_id = self._generate_id()
        importance = max(i.importance for i in kept_items)
        summary_item = MemoryItem(
            id=summary_id,
            content=summary_text,
            importance=importance,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            level=1,
            metadata={"type": "conversation_summary", "source_ids": stream_ids},
        )
        
        # Сохраняем в L1 (кэш + Redis hash + L1 summary list)
        self.l1_cache[summary_id] = summary_item
        await self.redis_store.l1_add_session(
            session_id=summary_id,
            summary=summary_text,
            importance=importance,
            source_ids=stream_ids,
        )
        await self.redis_store.l1_add_summary_entry(summary_id, summary_text, importance)
        
        # Одним вызовом в Graphiti с метаданными scale=meso
        if self.graphiti:
            try:
                episode_id = await self.graphiti.add_episode(
                    content=summary_text,
                    importance=importance,
                    source="l1_consolidation_summary",
                    metadata={"scale": "meso"},
                )
                self.last_episode_id = episode_id
            except Exception as exc:
                logger.warning(f"Failed to add summary to Graphiti: {exc}")
        
        # Помечаем как консолидированные в Redis
        await self.redis_store.l0_mark_consolidated(stream_ids)
        # Полностью очищаем L0 буфер в Redis и in-memory
        await self.redis_store.l0_clear_buffer()
        self.l0_cache.clear()
        
        result.promoted += 1
        return result

    async def _consolidate_l0_to_l1_locked(self) -> ConsolidationResult:
        """Обертка с локом для защиты от параллельных батчей."""
        async with self._consolidation_lock:
            return await self._consolidate_l0_to_l1()
    
    async def _consolidate_l0_to_l1_locked_wrapper(self, lock_key: Optional[str] = None) -> ConsolidationResult:
        """Обертка, которая освобождает Redis-lock после выполнения."""
        try:
            return await self._consolidate_l0_to_l1_locked()
        finally:
            if lock_key and self.redis_store and self.redis_store.client:
                try:
                    await self.redis_store.client.delete(lock_key)
                except Exception as exc:
                    logger.warning(f"Failed to release consolidation lock {lock_key}: {exc}")
    
    async def _consolidate_l1_to_l2(self) -> ConsolidationResult:
        """Консолидация L1 → L2 (граф)"""
        result = ConsolidationResult(promoted=0, decayed=0, deleted=0)
        now = datetime.now()
        
        items_to_remove = []
        
        for item_id, item in list(self.l1_cache.items()):
            age_hours = (now - item.created_at).total_seconds() / 3600
            
            # Рассчитать importance
            new_importance = self._calculate_importance(item, age_hours * 60)
            item.importance = new_importance
            
            # Критерии для L2 (только важное, дедуплицированное):
            # - Очень важно (>= 0.85)
            # - Или часто используется (>= 5 обращений)
            # - Или содержит ключевые факты
            should_promote = (
                new_importance >= 0.85 or 
                item.access_count >= 5 or
                self._contains_key_facts(item)
            )
            
            if should_promote:
                # Саммари уже отправлено в Graphiti на этапе L0→L1
                if item.metadata.get("type") == "conversation_summary":
                    items_to_remove.append(item_id)
                    result.decayed += 1
                    continue
                # Проверить на дубли перед сохранением
                if not await self._is_duplicate_in_l2(item):
                    # Сохранить в граф
                    merged_metadata = dict(item.metadata or {})
                    merged_metadata["access_count"] = item.access_count
                    merged_metadata["user_id"] = self.user_id
                    # Сохранить в L2 через GraphitiStore (новый API)
                    if self.graphiti:
                        await self.graphiti.add_episode(
                            content=item.content,
                            importance=new_importance,
                            source="l1_consolidation"
                        )
                    
                    items_to_remove.append(item_id)
                    result.promoted += 1
                    logger.info(f"Promoted to L2: {item_id[:8]}... (importance={new_importance:.2f})")
                else:
                    logger.debug(f"Skipped duplicate for L2: {item_id[:8]}...")
                
            elif new_importance < self.importance_threshold and age_hours > 2:
                # Удалить (забыть)
                items_to_remove.append(item_id)
                result.deleted += 1
                
            else:
                result.decayed += 1
        
        # Удалить обработанные
        for item_id in items_to_remove:
            self.l1_cache.pop(item_id, None)
        
        # Проверить capacity
        if len(self.l1_cache) > self.l1_capacity:
            # Удалить наименее важные
            sorted_items = sorted(
                self.l1_cache.items(),
                key=lambda x: x[1].importance
            )
            to_remove = len(self.l1_cache) - self.l1_capacity
            for item_id, _ in sorted_items[:to_remove]:
                self.l1_cache.pop(item_id, None)
                result.deleted += 1
        
        return result
    
    async def _apply_decay(self) -> None:
        """Применить decay ко всем уровням"""
        now = datetime.now()
        
        # L0 decay
        for item in self.l0_cache:
            age_minutes = (now - item.last_accessed).total_seconds() / 60
            item.importance *= np.exp(-self.decay_rate_l0 * age_minutes / 60)
        
        # L1 decay
        for item in self.l1_cache.values():
            age_hours = (now - item.last_accessed).total_seconds() / 3600
            item.importance *= np.exp(-self.decay_rate_l1 * age_hours)
        
        # L2/L3 decay в графе (через Cypher) — упрощённо для Episodic.
        # В текущей схеме Graphiti нет явных полей deleted/importance_score,
        # поэтому оставляем здесь задел для будущей логики decay.
        if self.graphiti and self._initialized:
            try:
                await self.graphiti.execute_cypher(
                    """
                    MATCH (ep:Episodic)
                    RETURN count(ep) as cnt
                    """,
                    {},
                )
            except Exception as exc:
                logger.warning(f"Failed to apply graph decay: {exc}")
    
    def _calculate_importance(
        self, 
        item: MemoryItem, 
        age_minutes: float
    ) -> float:
        """
        Рассчитать importance с учётом:
        - Temporal decay
        - Access count (reinforcement)
        """
        # Базовый decay
        decay_rate = self.decay_rate_l0 if item.level == 0 else self.decay_rate_l1
        temporal_decay = np.exp(-decay_rate * age_minutes / 60)
        
        # Reinforcement: частый доступ замедляет decay
        reinforcement = 1.0 + np.log1p(item.access_count) * 0.1
        
        # Итоговый importance
        new_importance = item.importance * temporal_decay * reinforcement
        
        return max(0.0, min(1.0, new_importance))
    
    # ═══════════════════════════════════════════════════════
    # ПОИСК
    # ═══════════════════════════════════════════════════════
    
    def _search_l0(self, query: str) -> List[SearchResult]:
        """Поиск в L0 (простой keyword matching)"""
        results = []
        query_lower = query.lower()
        
        for item in self.l0_cache:
            if query_lower in item.content.lower():
                results.append(SearchResult(
                    content=item.content,
                    score=item.importance,
                    source="l0",
                    level="l0",
                    timestamp=item.created_at,
                    metadata={"level": 0}
                ))
        
        return results
    
    def _search_l1(self, query: str) -> List[SearchResult]:
        """Поиск в L1"""
        results = []
        query_lower = query.lower()
        
        for item in self.l1_cache.values():
            if query_lower in item.content.lower():
                results.append(SearchResult(
                    content=item.content,
                    score=item.importance,
                    source="l1",
                    level="l1",
                    timestamp=item.created_at,
                    metadata={"level": 1}
                ))
        
        return results
    
    async def _update_access_counts(self, results: List[SearchResult]) -> None:
        """Обновить счётчики доступа для найденных результатов"""
        for result in results:
            level = result.metadata.get("level", 2)
            
            if level == 0:
                # L0
                for item in self.l0_cache:
                    if item.content == result.content:
                        item.access_count += 1
                        item.last_accessed = datetime.now()
                        break
                        
            elif level == 1:
                # L1
                for item in self.l1_cache.values():
                    if item.content == result.content:
                        item.access_count += 1
                        item.last_accessed = datetime.now()
                        break
    
    # ═══════════════════════════════════════════════════════
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Получить embedding для текста"""
        if self.embedding_func:
            return await self.embedding_func(text)
        return None
    
    def _generate_id(self) -> str:
        """Генерация уникального ID"""
        return str(uuid.uuid4())
    
    async def _summarize_batch(self, items: List[MemoryItem]) -> str:
        """
        LLM-сжатие батча (GPT-5 Mini). Жёсткий JSON-формат, чтобы модель не копировала логи.
        """
        # Готовим данные: нормализуем роли и убираем префиксы.
        lines: List[str] = []
        for it in items:
            raw = it.content or ""
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                role = "User"
                content = line
                low = line.lower()
                if low.startswith("user:"):
                    role = "User"
                    content = line[5:].strip()
                elif low.startswith("assistant:"):
                    role = "AI"
                    content = line[10:].strip()
                lines.append(f"{role}: {content}")
        text_block = "\n".join(lines)

        system_prompt = "You are a Data Processor. Output ONLY valid JSON."
        user_prompt = (
            f"DATA:\n{text_block}\n\n"
            "TASK: Summarize the data into a single 3rd-person paragraph.\n"
            "FORMAT: {\"summary\": \"The user discussed...\"}\n"
            "CONSTRAINT: Do not use timestamps or role labels in the summary value."
        )

        def _strip_code_blocks(text: str) -> str:
            t = text.strip() if text else ""
            if "```" in t:
                if "```json" in t:
                    t = t.split("```json", 1)[-1]
                t = t.split("```", 1)[-1]
            return t.strip()

        async def _call_llm() -> str:
            from openai import AsyncOpenAI  # type: ignore
            client = AsyncOpenAI()
            resp = await client.chat.completions.create(
                model=self._llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_completion_tokens=400,
            )
            if not resp.choices:
                return ""
            return resp.choices[0].message.content or ""

        try:
            raw_text = await _call_llm()
            cleaned = _strip_code_blocks(raw_text)
            try:
                data = json.loads(cleaned)
                summary = data.get("summary") if isinstance(data, dict) else None
                if summary and isinstance(summary, str):
                    return summary.strip()
            except Exception:
                pass
            if cleaned:
                return cleaned.strip()
        except Exception as exc:
            logger.warning(f"LLM summary failed, using fallback: {exc}")

        # Fallback: склеиваем содержимое без префиксов
        payload = []
        for line in lines:
            payload.append(line.split(":", 1)[1].strip() if ":" in line else line.strip())
        return " ".join(payload)[:2000] or "Summary unavailable."
    
    def _ensure_initialized(self):
        """Проверить инициализацию"""
        if not self._initialized:
            raise RuntimeError(
                "FractalMemory not initialized. "
                "Call await memory.initialize() first."
            )
    
    def _contains_key_facts(self, item: MemoryItem) -> bool:
        """Проверить содержит ли элемент ключевые факты."""
        key_patterns = [
            "меня зовут", "мое имя", "я ",
            "тебя зовут", "твое имя", "ты ",
            "запомни", "не забудь", "важно",
            "создатель", "разработчик",
            "проект", "цель", "задача",
        ]
        
        content = item.content.lower()
        return any(pattern in content for pattern in key_patterns)
    
    async def _is_duplicate_in_l2(self, item: MemoryItem) -> bool:
        """
        Проверяет, есть ли в Graphiti (Episodic) эпизод со схожим содержанием.
        
        Так как у нас нет отдельного поля user_id, фильтруем по user-тегу,
        который добавляется в content при сохранении эпизодов.
        """
        if not self.graphiti:
            return False
        
        snippet = item.content[:200].lower()
        user_tag = f"[user:{self.user_id}]"
        
        try:
            results = await self.graphiti.execute_cypher(
                """
                MATCH (ep:Episodic)
                WHERE ep.content CONTAINS $user_tag
                  AND toLower(ep.content) CONTAINS $snippet
                RETURN count(ep) AS cnt
                """,
                {"snippet": snippet, "user_tag": user_tag},
            )
            return bool(results and results[0].get("cnt", 0) > 0)
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════
    # СТАТИСТИКА
    # ═══════════════════════════════════════════════════════
    
    async def get_stats(self) -> Dict:
        """Получить статистику памяти (включая L2/L3 из Neo4j и L0/L1 из Redis)"""
        # Из Redis
        redis_stats = {}
        if self.redis_store:
            try:
                redis_stats = await self.redis_store.get_stats()
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
        
        stats = {
            "l0_size": redis_stats.get("l0_count", len(self.l0_cache)),
            "l0_capacity": self.l0_capacity,
            "l1_size": redis_stats.get("l1_count", len(self.l1_cache)),
            "l1_sessions": redis_stats.get("l1_sessions", 0),
            "l1_capacity": self.l1_capacity,
            "l0_avg_importance": float(np.mean([i.importance for i in self.l0_cache])) if self.l0_cache else 0.0,
            "l1_avg_importance": float(np.mean([i.importance for i in self.l1_cache.values()])) if self.l1_cache else 0.0,
            "l2_count": 0,
            "l3_count": 0,
            "user_id": self.user_id,
        }
        
        # Получить статистику из Graphiti (L2/L3)
        try:
            if self.graphiti and self._initialized:
                graph_stats = await self.graphiti.get_stats()
                stats["l2_count"] = graph_stats.get("l2_count", 0)
                stats["l3_count"] = graph_stats.get("l3_count", 0)
                stats["total_episodes"] = graph_stats.get("total_episodes", 0)
        except Exception as e:
            logger.warning(f"Failed to get Neo4j/Graphiti stats: {e}")
        
        return stats
    
    # ═══════════════════════════════════════════════════════
    # GARBAGE COLLECTION
    # ═══════════════════════════════════════════════════════
    
    async def garbage_collect(
        self,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Безопасная сборка мусора с учётом retention policies.
        
        Делегирует в GraphitiAdapter.safe_garbage_collect(), который:
        - Проверяет retention period по уровням (L0/L1/L2/L3)
        - Проверяет критичные связи перед удалением
        - Архивирует метаданные перед удалением
        
        Args:
            dry_run: Если True, только показывает что будет удалено
        
        Returns:
            Статистика GC
        """
        self._ensure_initialized()
        
        # Очистить L0/L1 (in-memory)
        cutoff_time = datetime.now() - timedelta(hours=24)
        l0_original = len(self.l0_cache)
        self.l0_cache = [
            item
            for item in self.l0_cache
            if item.created_at > cutoff_time or item.importance > 0.5
        ]
        l0_cleaned = l0_original - len(self.l0_cache)
        
        l1_original = len(self.l1_cache)
        self.l1_cache = {
            item_id: item
            for item_id, item in self.l1_cache.items()
            if item.last_accessed > cutoff_time or item.importance > 0.3
        }
        l1_cleaned = l1_original - len(self.l1_cache)
        
        # GC для графа (L2/L3) через GraphitiStore
        graph_stats = {"candidates": 0, "deleted": 0, "errors": []}
        if self.graphiti:
            try:
                retention_days = self.config.get("retention_days", 90)
                graph_stats = await self.graphiti.garbage_collect(
                    retention_days=retention_days,
                    dry_run=dry_run
                )
            except Exception as e:
                logger.warning(f"Graph GC failed: {e}")
                graph_stats["errors"].append(str(e))
        
        stats = {
            "l0_cleaned": l0_cleaned,
            "l1_cleaned": l1_cleaned,
            "graph_candidates": graph_stats.get("candidates", 0),
            "graph_deleted": graph_stats.get("deleted", 0),
            "graph_skipped_retention": graph_stats.get("skipped_retention", 0),
            "graph_skipped_links": graph_stats.get("skipped_links", 0),
            "dry_run": dry_run,
        }
        
        logger.info(
            f"GC {'(dry run) ' if dry_run else ''}"
            f"L0 cleaned={l0_cleaned}, L1 cleaned={l1_cleaned}, "
            f"graph deleted={graph_stats.get('deleted', 0)}"
        )
        return stats


# ═══════════════════════════════════════════════════════════
# ФАБРИКА
# ═══════════════════════════════════════════════════════════

def create_fractal_memory(config: Dict) -> FractalMemory:
    """
    Фабрика для создания FractalMemory.
    
    Args:
        config: Конфигурация (см. FractalMemory.__init__)
    
    Returns:
        FractalMemory instance
    """
    return FractalMemory(config)

