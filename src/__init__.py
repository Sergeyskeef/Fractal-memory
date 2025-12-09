"""
Fractal Memory - Autonomous memory system with self-learning for AI agents.

Основные компоненты:
- FractalMemory: Главный класс памяти с фрактальной иерархией (L0-L3)
- GraphitiStore: Хранилище L2/L3 через Graphiti (Neo4j)
- RedisMemoryStore: Хранилище L0/L1 через Redis
- ReasoningBank: Система самообучения на опыте
- SearchResult: Унифицированный результат поиска
"""

# Импортируем основные классы из core
from src.core.memory import FractalMemory, MemoryItem
from src.core.graphiti_store import GraphitiStore, SearchResult
from src.core.redis_store import RedisMemoryStore
from src.core.reasoning import ReasoningBank, Strategy
from src.core.embeddings import OpenAIEmbedder
from src.core.retrieval import HybridRetriever

# Импортируем типы
from src.core.types import Outcome

__version__ = "2.0.0"

__all__ = [
    # Основные классы
    "FractalMemory",
    "GraphitiStore",
    "RedisMemoryStore",
    "ReasoningBank",
    "HybridRetriever",
    
    # Модели данных
    "SearchResult",
    "MemoryItem",
    "Strategy",
    "Outcome",
    
    # Утилиты
    "OpenAIEmbedder",
    
    # Версия
    "__version__",
]
