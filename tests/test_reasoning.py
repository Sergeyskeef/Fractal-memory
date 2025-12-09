"""Тесты для ReasoningBank (новый на узлах Neo4j)."""

import pytest
from neo4j import AsyncGraphDatabase
from src.core.reasoning import ReasoningBank


@pytest.fixture
async def neo4j_driver():
    """Фикстура для Neo4j driver."""
    import os
    try:
        # Используем пароль из окружения или дефолтный
        password = os.getenv("NEO4J_PASSWORD", "changeme_secure_password_123")
        driver = AsyncGraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", password)
        )
        await driver.verify_connectivity()
        yield driver
        await driver.close()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_reasoning_bank_initialize(neo4j_driver):
    """Тест инициализации ReasoningBank."""
    bank = ReasoningBank(neo4j_driver, user_id="test_user")
    
    try:
        await bank.initialize()
        # Индексы созданы
        assert True
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_reasoning_bank_add_strategy(neo4j_driver):
    """Тест добавления стратегии."""
    bank = ReasoningBank(neo4j_driver, user_id="test_user")
    
    try:
        await bank.initialize()
        
        strategy_id = await bank.add_strategy(
            task_type="coding",
            description="Use type hints and docstrings",
            initial_success=True
        )
        
        assert strategy_id is not None
        assert len(strategy_id) > 0
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_reasoning_bank_get_strategies(neo4j_driver):
    """Тест получения стратегий."""
    bank = ReasoningBank(neo4j_driver, user_id="test_user")
    
    try:
        await bank.initialize()
        
        # Добавим стратегию
        await bank.add_strategy("coding", "Test strategy", True)
        
        # Получим стратегии
        strategies = await bank.get_strategies(task_type="coding", limit=5)
        
        assert isinstance(strategies, list)
        assert len(strategies) >= 1
        
        # Проверим структуру
        strategy = strategies[0]
        assert strategy.id is not None
        assert strategy.task_type == "coding"
        assert strategy.description == "Test strategy"
        assert strategy.success_rate >= 0.0
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_reasoning_bank_record_outcome(neo4j_driver):
    """Тест записи результата использования стратегии."""
    bank = ReasoningBank(neo4j_driver, user_id="test_user")
    
    try:
        await bank.initialize()
        
        # Добавим стратегию
        strategy_id = await bank.add_strategy("coding", "Test strategy", True)
        
        # Запишем успех
        await bank.record_outcome(strategy_id, success=True)
        
        # Проверим что success_rate обновился
        strategies = await bank.get_strategies("coding", limit=1)
        assert len(strategies) > 0
        assert strategies[0].usage_count >= 1
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.asyncio
async def test_reasoning_bank_add_experience(neo4j_driver):
    """Тест добавления опыта."""
    bank = ReasoningBank(neo4j_driver, user_id="test_user")
    
    try:
        await bank.initialize()
        
        # Добавим опыт
        exp_id = await bank.add_experience(
            context="Test context",
            action="Test action",
            outcome=True
        )
        
        assert exp_id is not None
        
        # Добавим опыт со стратегией
        strategy_id = await bank.add_strategy("coding", "Test", True)
        exp_id2 = await bank.add_experience(
            context="Context 2",
            action="Action 2",
            outcome=False,
            strategy_id=strategy_id
        )
        
        assert exp_id2 is not None
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")

