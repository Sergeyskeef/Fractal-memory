"""
Circuit Breaker для защиты от каскадных отказов.

Состояния:
- CLOSED: всё работает, запросы проходят
- OPEN: сервис упал, блокируем запросы (fail fast)
- HALF_OPEN: пробуем восстановить
"""

import time
import asyncio
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Circuit breaker открыт, запрос заблокирован"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.
    
    Использование:
        breaker = CircuitBreaker("neo4j", failure_threshold=5)
        
        try:
            result = await breaker.call(some_async_func, arg1, arg2)
        except CircuitBreakerOpenError:
            # Сервис недоступен
            return fallback_value
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Выполнить функцию через circuit breaker"""
        
        # Проверить состояние
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                logger.info(f"{self.name}: OPEN -> HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN"
                )
        
        # Попытка вызова
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _on_success(self):
        """Обработка успеха"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(f"{self.name}: HALF_OPEN -> CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self, error: Exception):
        """Обработка ошибки"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.error(f"{self.name}: HALF_OPEN -> OPEN")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.error(f"{self.name}: CLOSED -> OPEN")
            self.state = CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Состояние для мониторинга"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count
        }

