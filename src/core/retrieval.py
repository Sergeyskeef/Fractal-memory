"""
Hybrid Retrieval для Fractal Memory.

Комбинирует три стратегии поиска:
- Vector search (semantic similarity через Graphiti)
- Keyword search (fulltext через Neo4j)
- Graph traversal (связанные сущности)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Результат гибридного поиска."""
    content: str
    score: float
    source: str  # "vector", "keyword", "graph"
    metadata: Dict = field(default_factory=dict)
    episode_id: Optional[str] = None
    
    def __hash__(self):
        return hash(self.episode_id or self.content[:100])
    
    def __eq__(self, other):
        if not isinstance(other, RetrievalResult):
            return False
        if self.episode_id and other.episode_id:
            return self.episode_id == other.episode_id
        return self.content[:100] == other.content[:100]


class HybridRetriever:
    """
    Гибридный retriever для Fractal Memory.
    
    Комбинирует vector, keyword и graph поиск
    с использованием Reciprocal Rank Fusion.
    """
    
    DEFAULT_WEIGHTS = {
        "vector": 0.5,
        "keyword": 0.3,
        "graph": 0.2,
    }
    
    def __init__(
        self,
        graph_adapter,  # GraphitiAdapter / GraphitiStore
        user_id: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
        rrf_k: int = 60,  # RRF параметр
    ):
        self.graph = graph_adapter
        self.user_id = user_id
        self.user_tag = f"[user:{user_id}]" if user_id else None
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.rrf_k = rrf_k
        
        # Нормализовать веса
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    def _with_user_tag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Добавляет user_tag в параметры Cypher-запроса.
        Используем [user:<id>] из содержания эпизодов как суррогат user_id.
        """
        params = dict(params)
        params["user_tag"] = self.user_tag
        return params
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        weights: Optional[Dict[str, float]] = None,
        include_graph_expansion: bool = True,
    ) -> List[RetrievalResult]:
        """
        Гибридный поиск по всем стратегиям.
        
        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            weights: Переопределение весов (опционально)
            include_graph_expansion: Включить обход графа
        
        Returns:
            Отсортированный список результатов
        """
        weights = weights or self.weights
        
        # Нормализовать переданные веса
        if weights:
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}
        
        # Запустить все стратегии параллельно
        tasks = [
            self._vector_search(query, limit * 2),
            self._keyword_search(query, limit * 2),
            self._neo4j_search(query, limit * 2),  # Fallback поиск в Neo4j
        ]
        
        if include_graph_expansion:
            tasks.append(self._graph_search(query, limit))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собрать результаты по источникам
        vector_results = results[0] if not isinstance(results[0], Exception) else []
        keyword_results = results[1] if not isinstance(results[1], Exception) else []
        neo4j_results = results[2] if not isinstance(results[2], Exception) else []
        graph_results = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else []
        
        if isinstance(results[0], Exception):
            logger.warning(f"Vector search failed: {results[0]}")
        if isinstance(results[1], Exception):
            logger.warning(f"Keyword search failed: {results[1]}")
        if isinstance(results[2], Exception):
            logger.warning(f"Neo4j direct search failed: {results[2]}")
        if len(results) > 3 and isinstance(results[3], Exception):
            logger.warning(f"Graph search failed: {results[3]}")
        
        # Логирование для отладки
        logger.info(f"Search '{query[:30]}...': vector={len(vector_results)}, keyword={len(keyword_results)}, neo4j={len(neo4j_results)}, graph={len(graph_results)}")
        
        # Применить Reciprocal Rank Fusion
        fused = self._reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            graph_results=graph_results,
            neo4j_results=neo4j_results,
            weights=weights,
        )
        
        # Дедупликация и сортировка
        unique_results = self._deduplicate(fused)
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results[:limit]
    
    async def search_by_entity(
        self,
        entity_name: str,
        limit: int = 10,
    ) -> List[RetrievalResult]:
        """
        Поиск всех эпизодов, связанных с сущностью.
        """
        try:
            results = await self.graph.execute_cypher(
                """
                MATCH (e:Entity)-[r]-(ep:Episodic)
                WHERE toLower(e.name) CONTAINS toLower($name)
                  AND ($user_tag IS NULL OR ep.content CONTAINS $user_tag)
                RETURN DISTINCT ep.uuid as id,
                       ep.content as content,
                       type(r) as relation,
                       e.name as entity,
                       ep.created_at as created_at
                ORDER BY ep.created_at DESC
                LIMIT $limit
                """,
                self._with_user_tag({"name": entity_name, "limit": limit})
            )
            
            return [
                RetrievalResult(
                    content=r.get("content", ""),
                    score=1.0,
                    source="entity",
                    episode_id=r.get("id"),
                    metadata={
                        "entity": r.get("entity"),
                        "relation": r.get("relation"),
                        "created_at": r.get("created_at"),
                    }
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return []
    
    async def search_recent(
        self,
        hours: int = 24,
        limit: int = 10,
    ) -> List[RetrievalResult]:
        """
        Получить недавние эпизоды.
        """
        try:
            results = await self.graph.execute_cypher(
                """
                MATCH (ep:Episodic)
                WHERE ($user_tag IS NULL OR ep.content CONTAINS $user_tag)
                  AND ep.created_at > datetime() - duration({hours: $hours})
                RETURN ep.uuid as id,
                       ep.content as content,
                       ep.created_at as created_at
                ORDER BY ep.created_at DESC
                LIMIT $limit
                """,
                self._with_user_tag({"hours": hours, "limit": limit})
            )
            
            return [
                RetrievalResult(
                    content=r.get("content", ""),
                    score=1.0,
                    source="recent",
                    episode_id=r.get("id"),
                    metadata={"created_at": str(r.get("created_at", ""))}
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Recent search failed: {e}")
            return []
    
    async def _vector_search(
        self,
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        """
        Семантический поиск через Graphiti (L2/L3 в Neo4j).
        """
        try:
            logger.debug(f"Vector search for: {query[:50]}...")
            # Поддержка и GraphitiStore и GraphitiAdapter
            if hasattr(self.graph, 'search'):
                results = await self.graph.search(query, limit=limit)
                # GraphitiStore возвращает SearchResult с content, score, metadata
                # GraphitiAdapter возвращает SearchResult с content, relevance_score, metadata
                return [
                    RetrievalResult(
                        content=r.content,
                        score=getattr(r, 'score', getattr(r, 'relevance_score', 0.0)),
                        source="vector",
                        episode_id=r.metadata.get("uuid") if r.metadata else None,
                        metadata=r.metadata or {},
                    )
                    for r in results
                ]
            else:
                logger.warning("Graph adapter doesn't have search method")
                return []
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _neo4j_search(
        self,
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        """
        Прямой поиск в Neo4j (fallback если Graphiti не работает).
        Ищет по содержимому эпизодов.
        """
        try:
            # Простой поиск по подстроке
            results = await self.graph.execute_cypher(
                """
                MATCH (ep:Episodic)
                WHERE ($user_tag IS NULL OR ep.content CONTAINS $user_tag)
                  AND toLower(ep.content) CONTAINS toLower($query)
                RETURN ep.uuid as id,
                       ep.content as content,
                       0.5 as importance,
                       "episodic" as level
                ORDER BY ep.created_at DESC
                LIMIT $limit
                """,
                self._with_user_tag({"query": query, "limit": limit})
            )
            
            return [
                RetrievalResult(
                    content=r.get("content", ""),
                    score=r.get("importance", 0.5),
                    source="neo4j_direct",
                    episode_id=r.get("id"),
                    metadata={"level": r.get("level")},
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Neo4j direct search failed: {e}")
            return []
    
    async def _keyword_search(
        self,
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        """
        Полнотекстовый поиск через Neo4j.
        """
        try:
            # Экранировать специальные символы для Lucene
            safe_query = self._escape_lucene_query(query)
            
            results = await self.graph.execute_cypher(
                """
                CALL db.index.fulltext.queryNodes('episodic_content', $query)
                YIELD node, score
                WHERE ($user_tag IS NULL OR node.content CONTAINS $user_tag)
                RETURN node.uuid as id,
                       node.content as content,
                       score as relevance,
                       node.created_at as created_at
                LIMIT $limit
                """,
                self._with_user_tag({"query": safe_query, "limit": limit})
            )
            
            return [
                RetrievalResult(
                    content=r.get("content", ""),
                    score=r.get("relevance", 0.0),
                    source="keyword",
                    episode_id=r.get("id"),
                    metadata={
                        "raw_score": r.get("relevance", 0.0),
                        "created_at": r.get("created_at"),
                    },
                )
                for r in results
            ]
        except Exception as e:
            # Fulltext index может не существовать
            logger.warning(f"Keyword search failed (index may not exist): {e}")
            return []
    
    async def _graph_search(
        self,
        query: str,
        limit: int,
    ) -> List[RetrievalResult]:
        """
        Поиск через обход графа от найденных узлов.
        
        1. Найти начальные узлы через vector search
        2. Расширить через связи (CAUSED_BY, RELATES_TO, etc.)
        """
        try:
            # Сначала найти начальные точки
            initial = await self._vector_search(query, limit=5)
            if not initial:
                return []
            
            # Собрать episode_ids
            episode_ids = [
                r.episode_id for r in initial 
                if r.episode_id
            ]
            
            if not episode_ids:
                return []
            
            # Расширить через связи
            results = await self.graph.execute_cypher(
                """
                MATCH (ep:Episodic)-[r]-(related:Episodic)
                WHERE ep.uuid IN $ids
                  AND NOT related.uuid IN $ids
                  AND ($user_tag IS NULL OR related.content CONTAINS $user_tag)
                RETURN DISTINCT related.uuid as id,
                       related.content as content,
                       type(r) as relation,
                       count(r) as connection_strength
                ORDER BY connection_strength DESC, related.created_at DESC
                LIMIT $limit
                """,
                self._with_user_tag({"ids": episode_ids, "limit": limit})
            )
            
            return [
                RetrievalResult(
                    content=r.get("content", ""),
                    score=0.5 + r.get("connection_strength", 1) * 0.1,
                    source="graph",
                    episode_id=r.get("id"),
                    metadata={
                        "relation": r.get("relation"),
                        "connections": r.get("connection_strength", 1),
                    },
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult],
        graph_results: List[RetrievalResult],
        neo4j_results: List[RetrievalResult] = None,
        weights: Dict[str, float] = None,
    ) -> List[RetrievalResult]:
        """
        Объединить результаты используя Reciprocal Rank Fusion.
        
        RRF score = Σ (weight / (k + rank))
        """
        weights = weights or self.weights
        neo4j_results = neo4j_results or []
        
        scores: Dict[str, float] = {}
        results_map: Dict[str, RetrievalResult] = {}
        
        def add_results(results: List[RetrievalResult], weight: float):
            for rank, result in enumerate(results, start=1):
                key = result.episode_id or result.content[:100]
                rrf_score = weight / (self.rrf_k + rank)
                scores[key] = scores.get(key, 0) + rrf_score
                
                # Сохранить результат с лучшим score
                if key not in results_map or result.score > results_map[key].score:
                    results_map[key] = result

        add_results(vector_results, weights.get("vector", 0.5))
        add_results(keyword_results, weights.get("keyword", 0.3))
        add_results(graph_results, weights.get("graph", 0.2))
        add_results(neo4j_results, 0.4)  # Дать вес neo4j fallback
        
        # Обновить scores в результатах
        for key, result in results_map.items():
            result.score = scores[key]
        
        return list(results_map.values())
    
    def _deduplicate(
        self,
        results: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        """
        Удалить дубликаты, сохраняя лучший score.
        """
        seen: Dict[str, RetrievalResult] = {}
        
        for result in results:
            key = result.episode_id or result.content[:100]
            if key not in seen or result.score > seen[key].score:
                seen[key] = result
        
        return list(seen.values())
    
    @staticmethod
    def _escape_lucene_query(query: str) -> str:
        """
        Экранировать специальные символы Lucene.
        """
        special_chars = ['+', '-', '&&', '||', '!', '(', ')', '{', '}', 
                        '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']
        result = query
        for char in special_chars:
            result = result.replace(char, f'\\{char}')
        return result


# Фабрика
def create_hybrid_retriever(
    graph_adapter,
    user_id: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
) -> HybridRetriever:
    """Создать HybridRetriever."""
    return HybridRetriever(graph_adapter, user_id=user_id, weights=weights)

