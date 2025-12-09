"""
Unit tests для infrastructure компонентов.
"""

import pytest
import asyncio
import time

from src.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
)
from src.infrastructure.health import check_neo4j, check_redis, full_health_check


class DummyGraph:
    """Простой mock графа для health-check'ов."""

    async def initialize(self) -> None:
        return None

    async def execute_cypher(self, query: str, params: dict) -> list:
        # Для health-check достаточно успешно вернуть любой результат
        return [{"n": 1}]


# ═══════════════════════════════════════════════════════
# CIRCUIT BREAKER TESTS
# ═══════════════════════════════════════════════════════

class TestCircuitBreaker:
    """Тесты Circuit Breaker"""
    
    @pytest.fixture
    def breaker(self):
        """Создать Circuit Breaker"""
        return CircuitBreaker(
            name="test_service",
            failure_threshold=3,
            timeout=1,  # Короткий timeout для тестов
            success_threshold=2
        )
    
    @pytest.mark.asyncio
    async def test_closed_state_success(self, breaker):
        """CLOSED состояние: успешные вызовы проходят"""
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_closed_to_open(self, breaker):
        """CLOSED -> OPEN при превышении failure_threshold"""
        async def failing_func():
            raise Exception("Test error")
        
        # Вызвать несколько раз с ошибками
        for i in range(breaker.failure_threshold):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        # Должен быть OPEN
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_open_blocks_requests(self, breaker):
        """OPEN состояние блокирует запросы"""
        # Перевести в OPEN
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = time.time()
        
        async def func():
            return "should not execute"
        
        # Должен выбросить CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(func)
    
    @pytest.mark.asyncio
    async def test_open_to_half_open(self, breaker):
        """OPEN -> HALF_OPEN после timeout"""
        # Перевести в OPEN
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = time.time() - 2  # Прошло больше timeout
        
        async def func():
            return "success"
        
        # Должен перейти в HALF_OPEN и выполнить
        result = await breaker.call(func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_half_open_to_closed(self, breaker):
        """HALF_OPEN -> CLOSED после success_threshold успехов"""
        breaker.state = CircuitState.HALF_OPEN
        breaker.success_threshold = 2
        
        async def success_func():
            return "success"
        
        # Два успешных вызова
        await breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN  # Ещё не достаточно
        
        await breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED  # Теперь CLOSED
    
    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, breaker):
        """HALF_OPEN -> OPEN при неудаче"""
        breaker.state = CircuitState.HALF_OPEN
        
        async def failing_func():
            raise Exception("Test error")
        
        try:
            await breaker.call(failing_func)
        except Exception:
            pass
        
        assert breaker.state == CircuitState.OPEN
    
    def test_get_state(self, breaker):
        """get_state возвращает состояние"""
        state = breaker.get_state()
        
        assert state["name"] == "test_service"
        assert state["state"] == CircuitState.CLOSED.value
        assert "failure_count" in state
        assert "success_count" in state


# ═══════════════════════════════════════════════════════
# HEALTH CHECKS TESTS
# ═══════════════════════════════════════════════════════

class TestHealthChecks:
    """Тесты Health Checks"""
    
    @pytest.mark.asyncio
    async def test_check_neo4j_healthy(self):
        """Проверка Neo4j работает"""
        mock_graph = DummyGraph()
        await mock_graph.initialize()
        
        result = await check_neo4j(mock_graph)
        
        # Mock не поддерживает execute_cypher, но не должно быть ошибки
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_full_health_check(self):
        """Полная проверка здоровья"""
        mock_graph = DummyGraph()
        await mock_graph.initialize()
        
        components = {
            "graph": mock_graph
        }
        
        result = await full_health_check(components)
        
        assert "status" in result
        assert "components" in result
        assert "neo4j" in result["components"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_check_redis_with_sync_client(self):
        """check_redis корректно работает с sync Redis‑клиентом."""

        class SyncRedisClient:
            def __init__(self):
                self.ping_called = False

            def ping(self):
                self.ping_called = True
                return True

        client = SyncRedisClient()
        result = await check_redis(client)

        assert result["status"] in ("healthy", "unhealthy")
        # В нормальном случае ping должен быть вызван
        assert client.ping_called is True

