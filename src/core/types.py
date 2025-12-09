"""Общие перечисления и типы для Fractal Memory."""

from enum import Enum


class Outcome(Enum):
    """Результат выполнения действия."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

