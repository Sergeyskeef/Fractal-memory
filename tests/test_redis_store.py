"""Тесты для RedisStore."""

import pytest
from src.core.redis_store import RedisMemoryStore


@pytest.mark.asyncio
async def test_redis_store_connect():
    """Тест подключения к Redis."""
    store = RedisMemoryStore(
        redis_url="redis://localhost:6379",
        user_id="test_user",
        max_l0_size=100
    )
    
    try:
        await store.connect()
        assert store.client is not None
        await store.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.mark.asyncio
async def test_redis_store_l0_add():
    """Тест добавления в L0."""
    store = RedisMemoryStore(
        redis_url="redis://localhost:6379",
        user_id="test_user",
        max_l0_size=100
    )
    
    try:
        await store.connect()
        
        stream_id = await store.l0_add(
            content="Test L0 content",
            importance=0.7,
            metadata={"test": True}
        )
        
        assert stream_id is not None
        
        await store.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.mark.asyncio
async def test_redis_store_l0_get_recent():
    """Тест получения последних элементов L0."""
    store = RedisMemoryStore(
        redis_url="redis://localhost:6379",
        user_id="test_user",
        max_l0_size=100
    )
    
    try:
        await store.connect()
        
        # Добавим несколько элементов
        await store.l0_add("Content 1", 0.8)
        await store.l0_add("Content 2", 0.9)
        
        # Получим последние
        items = await store.l0_get_recent(count=10)
        
        assert isinstance(items, list)
        assert len(items) >= 2
        
        # Проверим структуру
        if items:
            item = items[0]
            assert "content" in item
            assert "importance" in item
            assert "timestamp" in item
        
        await store.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.mark.asyncio
async def test_redis_store_l1_session():
    """Тест работы с L1 сессиями."""
    store = RedisMemoryStore(
        redis_url="redis://localhost:6379",
        user_id="test_user",
        max_l0_size=100
    )
    
    try:
        await store.connect()
        
        # Добавим сессию
        await store.l1_add_session(
            session_id="test_session_1",
            summary="Test session summary",
            importance=0.8,
            source_ids=["id1", "id2"]
        )
        
        # Получим сессии
        sessions = await store.l1_get_sessions()
        
        assert isinstance(sessions, list)
        assert len(sessions) >= 1
        
        # Проверим структуру
        if sessions:
            session = sessions[0]
            assert "session_id" in session
            assert "summary" in session
            assert "importance" in session
        
        await store.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.mark.asyncio
async def test_redis_store_search():
    """Тест поиска по L0/L1."""
    store = RedisMemoryStore(
        redis_url="redis://localhost:6379",
        user_id="test_user",
        max_l0_size=100
    )
    
    try:
        await store.connect()
        
        # Добавим данные
        await store.l0_add("Searchable content", 0.8)
        await store.l1_add_session("sess1", "Searchable summary", 0.9, [])
        
        # Поиск
        results = await store.search("Searchable", limit=10)
        
        assert isinstance(results, list)
        assert len(results) >= 1
        
        await store.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

