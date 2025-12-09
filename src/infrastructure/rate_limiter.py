"""
Async rate limiter for external services (LLM, Neo4j, etc.).
"""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """
    Простой token-bucket rate limiter.
    Позволяет ограничить количество запросов за интервал времени.
    """

    def __init__(self, rate: int, per_seconds: float):
        if rate <= 0 or per_seconds <= 0:
            raise ValueError("rate и per_seconds должны быть больше нуля")
        self.capacity = rate
        self.tokens = float(rate)
        self.per_seconds = float(per_seconds)
        self.fill_rate = float(rate) / float(per_seconds)
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.updated_at = now
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.fill_rate,
        )

    async def acquire(self) -> None:
        """
        Ожидает пока появится свободный токен.
        """
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return

                missing = 1 - self.tokens
                wait_time = missing / self.fill_rate

            await asyncio.sleep(wait_time)


def rate_limit(limiter: Optional["RateLimiter"]):
    """
    Асинхронный контекстный менеджер для быстрого использования:

        async with rate_limit(limiter):
            await do_request()
    """

    class _RateLimitContext:
        def __init__(self, limiter):
            self._limiter = limiter

        async def __aenter__(self):
            if self._limiter:
                await self._limiter.acquire()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return _RateLimitContext(limiter)

