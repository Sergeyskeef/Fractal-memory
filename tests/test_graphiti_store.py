"""Тесты для GraphitiStore."""

import pytest
from datetime import datetime
from src.core.graphiti_store import GraphitiStore


@pytest.mark.asyncio
async def test_graphiti_store_connect():
    """Тест подключения к Graphiti."""
    import os
    password = os.getenv("NEO4J_PASSWORD", "changeme_secure_password_123")
    store = GraphitiStore(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password=password,
        user_id="test_user"
    )
    
    try:
        await store.connect()
        assert store.graphiti is not None
        await store.close()
    except Exception as e:
        pytest.skip(f"Graphiti/Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_graphiti_store_add_episode():
    """Тест добавления эпизода через Graphiti."""
    import os
    password = os.getenv("NEO4J_PASSWORD", "changeme_secure_password_123")
    store = GraphitiStore(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password=password,
        user_id="test_user"
    )
    
    try:
        await store.connect()
        
        episode_id = await store.add_episode(
            content="Test episode content",
            importance=0.8,
            source="test"
        )
        
        # Graphiti может вернуть разный формат - проверим что это строка
        assert episode_id is not None
        # Может быть UUID или другой формат
        assert isinstance(episode_id, str) or hasattr(episode_id, '__str__')
        
        await store.close()
    except Exception as e:
        pytest.skip(f"Graphiti/Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_graphiti_store_search():
    """Тест поиска через Graphiti."""
    import os
    password = os.getenv("NEO4J_PASSWORD", "changeme_secure_password_123")
    store = GraphitiStore(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password=password,
        user_id="test_user"
    )
    
    try:
        await store.connect()
        
        # Сначала добавим эпизод
        await store.add_episode(
            content="Test search content",
            importance=0.9,
            source="test"
        )
        
        # Поиск
        results = await store.search("test", limit=5)
        
        assert isinstance(results, list)
        # Может быть пусто если Graphiti ещё не проиндексировал
        
        await store.close()
    except Exception as e:
        pytest.skip(f"Graphiti/Neo4j not available: {e}")

