"""
Правильная работа с Graphiti.

КЛЮЧЕВОЕ ПРАВИЛО: ВСЁ пишем через Graphiti API, НЕ через Cypher напрямую!
Graphiti автоматически:
1. Извлекает сущности (entities)
2. Создаёт embeddings
3. Строит связи (edges)
4. Индексирует для поиска
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.nodes import EpisodeType

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Результат поиска по графу/эпизодам Graphiti."""

    content: str
    # Унифицированный скор релевантности (ранее мог называться relevance_score)
    score: float
    # Источник результата: "vector", "keyword", "graph", "neo4j_direct" и т.п.
    source: str
    # Уровень памяти / тип ноды: l0/l1/episodic/entity/unknown
    level: str = "unknown"
    # Временная метка (если доступна)
    timestamp: Optional[datetime] = None
    # Произвольные метаданные (uuid, raw_score и т.п.)
    metadata: Dict = field(default_factory=dict)


class GraphitiStore:
    """
    Хранилище L2/L3 через Graphiti.
    
    ВАЖНО: Не использовать execute_cypher для записи эпизодов!
    Только через add_episode() — иначе Graphiti не узнает о данных.
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, 
                 neo4j_password: str, user_id: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.user_id = user_id
        self.graphiti: Optional[Graphiti] = None
    
    async def connect(self) -> None:
        """Инициализировать Graphiti."""
        import os
        
        llm_client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            llm_client = OpenAIClient()
        else:
            logger.info("OPENAI_API_KEY not provided, Graphiti will run without LLM client")
        
        self.graphiti = Graphiti(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password,
            llm_client=llm_client,
        )
        logger.info(
            "Graphiti connected for user %s (indexes expected to be created via migrations)",
            self.user_id,
        )
    
    async def close(self) -> None:
        """Закрыть соединение."""
        if self.graphiti:
            await self.graphiti.close()
    
    async def add_episode(self, content: str, importance: float,
                          source: str = "conversation",
                          metadata: Optional[Dict] = None) -> str:
        """
        Добавить эпизод в L2 ЧЕРЕЗ Graphiti.
        
        НЕ ИСПОЛЬЗОВАТЬ Cypher напрямую — Graphiti не увидит эти данные!
        """
        episode_name = f"ep_{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Тегируем user_id для фильтрации при поиске
        tagged_content = f"[user:{self.user_id}] {content}"
        
        try:
            result = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=tagged_content,
                source_description=f"{source} | importance:{importance:.2f} | scale:{metadata.get('scale') if metadata else 'n/a'}",
                reference_time=datetime.now(),
                source=EpisodeType.message,
            )
            
            # Graphiti возвращает AddEpisodeResults с episode.uuid
            episode_uuid = result.episode.uuid if hasattr(result, 'episode') and hasattr(result.episode, 'uuid') else str(result.episode)

            # Проставляем scale вручную в узле Episodic, если указано
            if metadata and metadata.get("scale"):
                try:
                    await self.execute_cypher(
                        "MATCH (ep:Episodic {uuid: $id}) SET ep.scale = $scale",
                        {"id": episode_uuid, "scale": metadata["scale"]},
                    )
                except Exception as exc:
                    logger.warning(f"Failed to set scale on episodic node: {exc}")

            logger.info(f"Episode added to L2 via Graphiti: {episode_uuid[:8] if isinstance(episode_uuid, str) else 'unknown'}...")
            return episode_uuid
            
        except Exception as e:
            logger.error(f"Failed to add episode via Graphiti: {e}")
            raise
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Поиск через Graphiti.
        
        Graphiti использует:
        - Vector similarity (embeddings)
        - BM25 keyword search
        - Graph traversal
        
        Без LLM-вызовов! ~300ms latency.
        """
        try:
            results = await self.graphiti.search(
                query=query,
                num_results=limit * 2,  # Берём больше, фильтруем по user
            )
            
            search_results = []
            for edge in results:
                fact = getattr(edge, 'fact', '') or ''
                
                # Фильтруем по user_id
                if f"[user:{self.user_id}]" not in fact and self.user_id not in str(edge):
                    continue
                
                # Убираем тег из результата
                clean_fact = fact.replace(f"[user:{self.user_id}]", "").strip()
                
                search_results.append(SearchResult(
                    content=clean_fact,
                    score=getattr(edge, 'score', 1.0),
                    source="graphiti",
                    metadata={
                        "uuid": getattr(edge, 'uuid', None),
                    }
                ))
            
            return search_results[:limit]
            
        except Exception as e:
            logger.error(f"Graphiti search failed: {e}")
            return []
    
    async def execute_cypher(self, query: str, params: Dict = None) -> List[Dict]:
        """
        Выполнить Cypher запрос (для совместимости со старым кодом).
        
        ВАЖНО: Использовать только для чтения/статистики, НЕ для записи эпизодов!
        Для записи использовать add_episode().
        """
        if not self.graphiti:
            raise RuntimeError("GraphitiStore not connected")
        
        driver = self.graphiti.driver
        async with driver.session() as session:
            result = await session.run(query, params or {})
            records = []
            async for record in result:
                records.append(dict(record))
            return records
    
    async def get_stats(self) -> Dict[str, int]:
        """Статистика из Graphiti / Neo4j (только для текущего пользователя)."""
        stats: Dict[str, int] = {
            "l2_count": 0,
            "l3_count": 0,
            "total_episodes": 0,
            "total_entities": 0,
        }

        try:
            user_tag = f"[user:{self.user_id}]"
            
            # Считаем только Episodic-узлы текущего пользователя (эпизоды L2)
            episodic = await self.execute_cypher(
                "MATCH (n:Episodic) WHERE n.content CONTAINS $user_tag RETURN count(n) as count",
                {"user_tag": user_tag},
            )
            if episodic:
                stats["l2_count"] = episodic[0].get("count", 0) or 0
                stats["total_episodes"] = stats["l2_count"]

            # Считаем только Entity-узлы, связанные с эпизодами пользователя (семантические сущности L3)
            # Entity могут быть общими, но мы считаем только те, что связаны с эпизодами пользователя
            entities = await self.execute_cypher(
                """
                MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity)
                WHERE ep.content CONTAINS $user_tag
                RETURN count(DISTINCT e) as count
                """,
                {"user_tag": user_tag},
            )
            if entities:
                stats["l3_count"] = entities[0].get("count", 0) or 0
                stats["total_entities"] = stats["l3_count"]

        except Exception as e:
            logger.warning(f"Failed to get stats from Graphiti: {e}")

        return stats
    
    async def garbage_collect(
        self, 
        retention_days: int = 90,
        dry_run: bool = False
    ) -> Dict:
        """
        Безопасная сборка мусора для графа (Retention Policy).
        
        Удаляет старые эпизоды, которые:
        1. Созданы более retention_days дней назад
        2. Не обновлялись (valid_at) более retention_days дней
        
        ВАЖНО: Graphiti не имеет поля deleted, поэтому используем прямое удаление
        по возрасту. Это безопасно, т.к. старые эпизоды уже не используются.
        
        Args:
            retention_days: Сколько дней хранить эпизоды (по умолчанию 90)
            dry_run: Если True, только показывает что будет удалено
            
        Returns:
            Статистика GC: {"candidates": int, "deleted": int, "errors": List[str]}
        """
        stats = {"candidates": 0, "deleted": 0, "errors": []}
        
        if not self.graphiti:
            stats["errors"].append("GraphitiStore not connected")
            return stats
        
        try:
            # Найти кандидатов на удаление: старые эпизоды без недавних обновлений
            # Используем valid_at (обновляется при recall) или created_at как fallback
            candidates_query = """
                MATCH (ep:Episodic)
                WHERE ep.content CONTAINS $user_tag
                  AND (
                    (ep.valid_at IS NOT NULL AND ep.valid_at < datetime() - duration({days: $days}))
                    OR 
                    (ep.valid_at IS NULL AND ep.created_at < datetime() - duration({days: $days}))
                  )
                RETURN ep.uuid as uuid, 
                       ep.created_at as created_at,
                       ep.valid_at as valid_at
                LIMIT 1000
            """
            
            user_tag = f"[user:{self.user_id}]"
            candidates = await self.execute_cypher(
                candidates_query,
                {"days": retention_days, "user_tag": user_tag}
            )
            
            stats["candidates"] = len(candidates)
            
            if dry_run:
                logger.info(f"GC dry run: found {stats['candidates']} candidates for deletion")
                return stats
            
            if not candidates:
                logger.debug("No candidates for GC")
                return stats
            
            # Удалить кандидатов (DETACH DELETE удаляет связи автоматически)
            uuids_to_delete = [c["uuid"] for c in candidates if c.get("uuid")]
            
            if uuids_to_delete:
                # Двойная проверка: удаляем только узлы с user_tag (безопасность)
                delete_query = """
                    MATCH (ep:Episodic)
                    WHERE ep.uuid IN $uuids
                      AND ep.content CONTAINS $user_tag
                    DETACH DELETE ep
                    RETURN count(ep) as deleted_count
                """
                
                delete_result = await self.execute_cypher(
                    delete_query,
                    {"uuids": uuids_to_delete, "user_tag": user_tag}
                )
                
                if delete_result:
                    stats["deleted"] = delete_result[0].get("deleted_count", 0)
                    logger.info(
                        f"GC completed: deleted {stats['deleted']} episodes "
                        f"(retention={retention_days} days)"
                    )
                    
        except Exception as e:
            error_msg = f"Graph GC failed: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            
        return stats

