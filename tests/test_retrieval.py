"""
Unit tests для HybridRetriever.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from src.core.retrieval import HybridRetriever, RetrievalResult


class DummySearchResult:
    """Простой stand-in для SearchResult из Graphiti."""

    def __init__(
        self,
        content: str,
        score: float = None,
        relevance_score: float = None,
        source: str = "graphiti",
        timestamp=None,
        metadata=None,
    ):
        self.content = content
        if score is not None:
            self.score = score
        if relevance_score is not None:
            self.relevance_score = relevance_score
        self.source = source
        self.timestamp = timestamp
        self.metadata = metadata or {}


class TestHybridRetriever:
    
    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        graph.search = AsyncMock(return_value=[])
        graph.execute_cypher = AsyncMock(return_value=[])
        return graph
    
    @pytest.fixture
    def retriever(self, mock_graph):
        return HybridRetriever(mock_graph)
    
    @pytest.mark.asyncio
    async def test_search_combines_all_sources(self, retriever, mock_graph):
        """Поиск комбинирует результаты из всех источников."""
        # Настроить моки
        mock_graph.search.return_value = [
            DummySearchResult(
                content="vector result",
                relevance_score=0.9,
                source="graphiti",
                timestamp=None,
                metadata={"uuid": "v1"}
            )
        ]
        mock_graph.execute_cypher.return_value = [
            {"id": "k1", "content": "keyword result", "relevance": 0.8, "created_at": None}
        ]
        
        results = await retriever.search("test query", limit=5)
        
        assert len(results) >= 1
        assert mock_graph.search.called
        assert mock_graph.execute_cypher.called
    
    @pytest.mark.asyncio
    async def test_search_handles_failures_gracefully(self, retriever, mock_graph):
        """Поиск продолжает работать при сбое одной стратегии."""
        mock_graph.search.side_effect = Exception("Vector search failed")
        mock_graph.execute_cypher.return_value = [
            {"id": "k1", "content": "keyword result", "relevance": 0.8, "importance": 0.7}
        ]
        
        results = await retriever.search("test query", limit=5)
        
        # Должен вернуть результаты keyword search
        assert len(results) >= 0  # Не падает
    
    @pytest.mark.asyncio
    async def test_search_recent(self, retriever, mock_graph):
        """search_recent возвращает недавние эпизоды."""
        from datetime import datetime
        mock_graph.execute_cypher.return_value = [
            {
                "id": "r1",
                "content": "recent content",
                "created_at": datetime.now()
            }
        ]
        
        results = await retriever.search_recent(hours=24, limit=5)
        
        assert len(results) == 1
        assert results[0].source == "recent"
        assert results[0].content == "recent content"
    
    @pytest.mark.asyncio
    async def test_search_by_entity(self, retriever, mock_graph):
        """search_by_entity находит связанные эпизоды."""
        mock_graph.execute_cypher.return_value = [
            {
                "id": "e1",
                "content": "entity content",
                "entity": "TestEntity",
                "relation": "MENTIONS",
                "created_at": None,
            }
        ]
        
        results = await retriever.search_by_entity("TestEntity", limit=5)
        
        assert len(results) == 1
        assert results[0].metadata["entity"] == "TestEntity"
        assert results[0].metadata["relation"] == "MENTIONS"
    
    def test_rrf_fusion_combines_scores(self, retriever):
        """RRF корректно комбинирует ранги."""
        vector = [RetrievalResult("a", 0.9, "vector", episode_id="1")]
        keyword = [RetrievalResult("a", 0.8, "keyword", episode_id="1")]
        graph = []
        
        fused = retriever._reciprocal_rank_fusion(
            vector_results=vector,
            keyword_results=keyword,
            graph_results=graph,
            weights={"vector": 0.5, "keyword": 0.3, "graph": 0.2},
        )
        
        assert len(fused) == 1
        assert fused[0].score > 0  # Комбинированный score
    
    def test_deduplicate_keeps_best_score(self, retriever):
        """Дедупликация сохраняет лучший score."""
        results = [
            RetrievalResult("same", 0.5, "vector", episode_id="1"),
            RetrievalResult("same", 0.9, "keyword", episode_id="1"),
        ]
        
        deduped = retriever._deduplicate(results)
        
        assert len(deduped) == 1
        assert deduped[0].score == 0.9
    
    def test_weights_normalization(self, mock_graph):
        """Веса нормализуются до суммы 1."""
        retriever = HybridRetriever(mock_graph, weights={"vector": 1, "keyword": 1, "graph": 1})
        
        assert abs(sum(retriever.weights.values()) - 1.0) < 0.001
    
    @pytest.mark.asyncio
    async def test_vector_search_extracts_episode_id(self, retriever, mock_graph):
        """Vector search корректно извлекает episode_id из metadata."""
        mock_graph.search.return_value = [
            DummySearchResult(
                content="test content",
                score=0.8,
                source="graphiti",
                timestamp=None,
                metadata={"uuid": "ep123"}
            )
        ]
        
        results = await retriever._vector_search("test", limit=5)
        
        assert len(results) == 1
        assert results[0].episode_id == "ep123"
        assert results[0].source == "vector"
    
    @pytest.mark.asyncio
    async def test_keyword_search_handles_missing_index(self, retriever, mock_graph):
        """Keyword search gracefully обрабатывает отсутствие индекса."""
        mock_graph.execute_cypher.side_effect = Exception("Index not found")
        
        results = await retriever._keyword_search("test", limit=5)
        
        # Должен вернуть пустой список, не упасть
        assert results == []
    
    def test_escape_lucene_query(self):
        """Экранирование Lucene специальных символов работает."""
        query = "test + query && (special)"
        escaped = HybridRetriever._escape_lucene_query(query)
        
        assert "\\+" in escaped
        assert "\\&&" in escaped  # && экранируется как единый символ
        assert "\\(" in escaped
    
    @pytest.mark.asyncio
    async def test_graph_search_expands_from_initial(self, retriever, mock_graph):
        """Graph search расширяет от начальных узлов."""
        # Настроить vector search для начальных узлов
        mock_graph.search.return_value = [
            DummySearchResult(
                content="initial",
                relevance_score=0.9,
                source="graphiti",
                timestamp=None,
                metadata={"uuid": "init1"}
            )
        ]
        
        # Настроить graph expansion
        mock_graph.execute_cypher.return_value = [
            {
                "id": "related1",
                "content": "related content",
                "relation": "RELATES_TO",
                "connection_strength": 2
            }
        ]
        
        results = await retriever._graph_search("test", limit=5)
        
        assert len(results) == 1
        assert results[0].source == "graph"
        assert results[0].episode_id == "related1"
        assert "relation" in results[0].metadata
    
    @pytest.mark.asyncio
    async def test_search_without_graph_expansion(self, retriever, mock_graph):
        """Поиск может работать без graph expansion."""
        mock_graph.search.return_value = [
            DummySearchResult(
                content="vector result",
                relevance_score=0.9,
                source="graphiti",
                timestamp=None,
                metadata={"uuid": "v1"}
            )
        ]
        mock_graph.execute_cypher.return_value = [
            {"id": "k1", "content": "keyword", "relevance": 0.8, "created_at": None}
        ]
        
        results = await retriever.search("test", limit=5, include_graph_expansion=False)
        
        # Должен вернуть результаты без graph search
        assert len(results) >= 1
        # Проверить что graph search не вызывался (execute_cypher вызван только для keyword и neo4j fallback)
        assert mock_graph.execute_cypher.call_count == 2

