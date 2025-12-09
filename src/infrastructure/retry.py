"""
Utility decorators for async retries with exponential backoff.
"""

import asyncio
import random
from functools import wraps
from typing import Iterable, Tuple, Type


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    jitter: float = 0.1,
):
    """
    Асинхронный декоратор с экспоненциальной задержкой.

    Args:
        max_attempts: Максимум попыток
        base_delay: Начальная задержка между попытками
        exceptions: Кортеж исключений для перехвата
        jitter: Добавочный случайный шум
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 1
            delay = base_delay

            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt >= max_attempts:
                        raise

                    await asyncio.sleep(delay + random.uniform(0, jitter))
                    attempt += 1
                    delay *= 2

        return wrapper

    return decorator

