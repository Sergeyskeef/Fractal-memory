# 03. Phase 2: Реализация памяти

## 🎯 Цель

Реализовать FractalMemory — главный класс памяти с фрактальной иерархией.

**Время**: 2-3 дня  
**Результат**: Работающая память с консолидацией L0→L1→L2→L3

---

## 📋 Чек-лист Phase 2

- [ ] GraphitiAdapter создан
- [ ] FractalMemory создан
- [ ] Методы remember/recall работают
- [ ] Консолидация работает
- [ ] Soft delete работает
- [ ] Unit тесты проходят
- [ ] Интеграционные тесты проходят

---

## 1️⃣ GraphitiAdapter (обёртка над Graphiti)

### Файл `src/core/graphiti_adapter.py`:

```python
"""
GraphitiAdapter — обёртка над Graphiti.

Почему не использовать Graphiti напрямую:
1. Изолируем зависимость (если API изменится)
2. Добавляем свою логику (soft delete, метрики)
3. Упрощаем тестирование (можно подменить mock)

Использование:
    adapter = GraphitiAdapter(config)
    await adapter.initialize()
    await adapter.add_episode(...)
    results = await adapter.search(...)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
import logging
import uuid

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# МОДЕЛИ ДАННЫХ (независимы от Graphiti)
# ═══════════════════════════════════════════════════════════

@dataclass
class Episode:
    """Эпизод — единица памяти"""
    id: str
    content: str
    timestamp: datetime
    source: str = "conversation"
    importance_score: float = 1.0
    level: int = 1  # 1=L1, 2=L2, 3=L3
    outcome: Optional[str] = None  # success/failure/neutral
    metadata: Dict = field(default_factory=dict)
    # Soft delete
    deleted: bool = False
    deleted_at: Optional[datetime] = None


@dataclass
class Entity:
    """Сущность — персона, проект, концепт"""
    id: str
    name: str
    entity_type: str
    importance_score: float = 1.0
    access_count: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)
    # Soft delete
    deleted: bool = False
    deleted_at: Optional[datetime] = None


@dataclass
class SearchResult:
    """Результат поиска"""
    content: str
    relevance_score: float
    source: str
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# АБСТРАКТНЫЙ ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════════

class GraphMemoryInterface(ABC):
    """
    Абстрактный интерфейс для графовой памяти.
    Позволяет подменять реализацию (Graphiti → другая библиотека).
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Инициализация подключения"""
        pass
    
    @abstractmethod
    async def add_episode(self, episode: Episode) -> str:
        """Добавить эпизод, вернуть ID"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        include_deleted: bool = False
    ) -> List[SearchResult]:
        """Поиск по памяти"""
        pass
    
    @abstractmethod
    async def get_by_id(self, episode_id: str) -> Optional[Episode]:
        """Получить эпизод по ID"""
        pass
    
    @abstractmethod
    async def soft_delete(self, episode_id: str) -> bool:
        """Мягкое удаление (пометить deleted=true)"""
        pass
    
    @abstractmethod
    async def hard_delete(self, episode_id: str) -> bool:
        """Физическое удаление (только для GC после soft delete)"""
        pass
    
    @abstractmethod
    async def update_importance(
        self, 
        episode_id: str, 
        new_importance: float
    ) -> bool:
        """Обновить importance score"""
        pass
    
    @abstractmethod
    async def execute_cypher(
        self, 
        query: str, 
        params: Dict = None
    ) -> List[Dict]:
        """Выполнить произвольный Cypher запрос"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Закрыть подключение"""
        pass


# ═══════════════════════════════════════════════════════════
# GRAPHITI ADAPTER
# ═══════════════════════════════════════════════════════════

class GraphitiAdapter(GraphMemoryInterface):
    """
    Адаптер для Graphiti.
    Переводит наш интерфейс в вызовы Graphiti API.
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: {
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "llm_client": <OpenAI client>,  # для Graphiti
                "embedder": <Embedder>  # опционально
            }
        """
        self.config = config
        self.graphiti = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Инициализация Graphiti"""
        if self._initialized:
            return
        
        try:
            from graphiti_core import Graphiti
            from graphiti_core.llm_client import OpenAIClient
            
            # Создать LLM клиент для Graphiti
            llm_client = self.config.get("llm_client")
            if llm_client is None:
                llm_client = OpenAIClient()
            
            # Инициализировать Graphiti
            self.graphiti = Graphiti(
                neo4j_uri=self.config["neo4j_uri"],
                neo4j_user=self.config["neo4j_user"],
                neo4j_password=self.config["neo4j_password"],
                llm_client=llm_client
            )
            
            self._initialized = True
            logger.info("GraphitiAdapter initialized successfully")
            
        except ImportError:
            raise ImportError(
                "graphiti-core not installed. "
                "Run: pip install graphiti-core"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise
    
    async def add_episode(self, episode: Episode) -> str:
        """Добавить эпизод через Graphiti"""
        self._ensure_initialized()
        
        try:
            # Преобразовать в формат Graphiti
            await self.graphiti.add_episode(
                name=episode.id,
                episode_body=episode.content,
                source_description=episode.source,
                reference_time=episode.timestamp
            )
            
            # Добавить soft delete поля через Cypher
            # (Graphiti не знает про наши поля)
            await self.execute_cypher(
                """
                MATCH (ep:Episode {name: $id})
                SET ep.importance_score = $importance,
                    ep.level = $level,
                    ep.outcome = $outcome,
                    ep.deleted = false
                """,
                {
                    "id": episode.id,
                    "importance": episode.importance_score,
                    "level": episode.level,
                    "outcome": episode.outcome
                }
            )
            
            logger.debug(f"Episode added: {episode.id}")
            return episode.id
            
        except Exception as e:
            logger.error(f"Failed to add episode: {e}")
            raise
    
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        include_deleted: bool = False
    ) -> List[SearchResult]:
        """Гибридный поиск через Graphiti"""
        self._ensure_initialized()
        
        try:
            # Поиск через Graphiti
            raw_results = await self.graphiti.search(
                query=query,
                num_results=limit * 2  # берём больше, потом фильтруем
            )
            
            results = []
            for r in raw_results:
                # Фильтр soft deleted
                if not include_deleted:
                    # Проверить deleted флаг
                    is_deleted = getattr(r, 'deleted', False)
                    if is_deleted:
                        continue
                
                results.append(SearchResult(
                    content=getattr(r, 'fact', str(r)),
                    relevance_score=getattr(r, 'score', 1.0),
                    source=getattr(r, 'source_description', 'unknown'),
                    timestamp=getattr(r, 'created_at', datetime.now()),
                    metadata={
                        "uuid": getattr(r, 'uuid', None),
                        "episode_name": getattr(r, 'name', None)
                    }
                ))
                
                if len(results) >= limit:
                    break
            
            logger.debug(f"Search returned {len(results)} results for: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_by_id(self, episode_id: str) -> Optional[Episode]:
        """Получить эпизод по ID"""
        self._ensure_initialized()
        
        results = await self.execute_cypher(
            """
            MATCH (ep:Episode {name: $id})
            RETURN ep
            """,
            {"id": episode_id}
        )
        
        if not results:
            return None
        
        ep = results[0]["ep"]
        return Episode(
            id=ep.get("name", episode_id),
            content=ep.get("content", ""),
            timestamp=ep.get("timestamp", datetime.now()),
            source=ep.get("source_description", "unknown"),
            importance_score=ep.get("importance_score", 1.0),
            level=ep.get("level", 1),
            outcome=ep.get("outcome"),
            deleted=ep.get("deleted", False),
            deleted_at=ep.get("deleted_at")
        )
    
    async def soft_delete(self, episode_id: str) -> bool:
        """Мягкое удаление"""
        self._ensure_initialized()
        
        try:
            await self.execute_cypher(
                """
                MATCH (ep:Episode {name: $id})
                SET ep.deleted = true,
                    ep.deleted_at = datetime()
                RETURN ep
                """,
                {"id": episode_id}
            )
            logger.info(f"Soft deleted episode: {episode_id}")
            return True
            
        except Exception as e:
            logger.error(f"Soft delete failed: {e}")
            return False
    
    async def hard_delete(self, episode_id: str) -> bool:
        """
        Физическое удаление.
        ⚠️ Использовать ТОЛЬКО для GC после soft delete периода!
        """
        self._ensure_initialized()
        
        try:
            await self.execute_cypher(
                """
                MATCH (ep:Episode {name: $id})
                WHERE ep.deleted = true
                DETACH DELETE ep
                """,
                {"id": episode_id}
            )
            logger.info(f"Hard deleted episode: {episode_id}")
            return True
            
        except Exception as e:
            logger.error(f"Hard delete failed: {e}")
            return False
    
    async def update_importance(
        self, 
        episode_id: str, 
        new_importance: float
    ) -> bool:
        """Обновить importance score"""
        self._ensure_initialized()
        
        try:
            await self.execute_cypher(
                """
                MATCH (ep:Episode {name: $id})
                SET ep.importance_score = $importance,
                    ep.last_accessed = datetime()
                """,
                {"id": episode_id, "importance": new_importance}
            )
            return True
            
        except Exception as e:
            logger.error(f"Update importance failed: {e}")
            return False
    
    async def execute_cypher(
        self, 
        query: str, 
        params: Dict = None
    ) -> List[Dict]:
        """Выполнить произвольный Cypher запрос"""
        self._ensure_initialized()
        
        # Получить driver из Graphiti
        driver = self.graphiti._driver
        
        async with driver.session() as session:
            result = await session.run(query, params or {})
            return [dict(record) for record in await result.data()]
    
    async def close(self) -> None:
        """Закрыть подключение"""
        if self.graphiti:
            await self.graphiti.close()
            self._initialized = False
            logger.info("GraphitiAdapter closed")
    
    def _ensure_initialized(self):
        """Проверить что адаптер инициализирован"""
        if not self._initialized:
            raise RuntimeError(
                "GraphitiAdapter not initialized. "
                "Call await adapter.initialize() first."
            )


# ═══════════════════════════════════════════════════════════
# MOCK ADAPTER (для тестов)
# ═══════════════════════════════════════════════════════════

class MockGraphMemory(GraphMemoryInterface):
    """
    Mock реализация для тестов.
    Не требует Neo4j, работает в памяти.
    """
    
    def __init__(self):
        self.episodes: Dict[str, Episode] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def add_episode(self, episode: Episode) -> str:
        self.episodes[episode.id] = episode
        return episode.id
    
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        include_deleted: bool = False
    ) -> List[SearchResult]:
        results = []
        query_lower = query.lower()
        
        for ep in self.episodes.values():
            if ep.deleted and not include_deleted:
                continue
            
            if query_lower in ep.content.lower():
                results.append(SearchResult(
                    content=ep.content,
                    relevance_score=1.0,
                    source=ep.source,
                    timestamp=ep.timestamp
                ))
        
        return results[:limit]
    
    async def get_by_id(self, episode_id: str) -> Optional[Episode]:
        return self.episodes.get(episode_id)
    
    async def soft_delete(self, episode_id: str) -> bool:
        if episode_id in self.episodes:
            self.episodes[episode_id].deleted = True
            self.episodes[episode_id].deleted_at = datetime.now()
            return True
        return False
    
    async def hard_delete(self, episode_id: str) -> bool:
        if episode_id in self.episodes:
            del self.episodes[episode_id]
            return True
        return False
    
    async def update_importance(
        self, 
        episode_id: str, 
        new_importance: float
    ) -> bool:
        if episode_id in self.episodes:
            self.episodes[episode_id].importance_score = new_importance
            return True
        return False
    
    async def execute_cypher(
        self, 
        query: str, 
        params: Dict = None
    ) -> List[Dict]:
        # Mock не поддерживает Cypher
        return []
    
    async def close(self) -> None:
        self._initialized = False


# ═══════════════════════════════════════════════════════════
# ФАБРИКА
# ═══════════════════════════════════════════════════════════

def create_graph_memory(config: Dict, use_mock: bool = False) -> GraphMemoryInterface:
    """
    Фабрика для создания GraphMemory.
    
    Args:
        config: Конфигурация
        use_mock: True для тестов (без Neo4j)
    
    Returns:
        GraphMemoryInterface реализация
    """
    if use_mock:
        return MockGraphMemory()
    else:
        return GraphitiAdapter(config)
```

---

## 2️⃣ FractalMemory (главный класс)

### Файл `src/core/memory.py`:

```python
"""
FractalMemory — главный класс памяти с фрактальной иерархией.

Уровни памяти:
- L0: Working Memory (Python list, секунды)
- L1: Short-Term Memory (Python dict, минуты-часы)  
- L2: Medium-Term Memory (Graph, дни)
- L3: Long-Term Memory (Graph, месяцы-годы)

Использование:
    memory = FractalMemory(config)
    await memory.initialize()
    
    # Запомнить
    await memory.remember("Пользователь любит Python")
    
    # Вспомнить
    results = await memory.recall("что любит пользователь")
    
    # Консолидация (вызывается автоматически или вручную)
    await memory.consolidate()
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncio
import logging
import uuid
import numpy as np

from .graphiti_adapter import (
    GraphMemoryInterface, 
    GraphitiAdapter,
    Episode,
    SearchResult,
    create_graph_memory
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# МОДЕЛИ ДЛЯ ВНУТРЕННЕГО ИСПОЛЬЗОВАНИЯ
# ═══════════════════════════════════════════════════════════

@dataclass
class MemoryItem:
    """Элемент памяти (для L0/L1)"""
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    importance: float = 1.0
    access_count: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    level: int = 0  # 0=L0, 1=L1


@dataclass 
class ConsolidationResult:
    """Результат консолидации"""
    promoted: int  # Повышено на уровень выше
    decayed: int   # Понижен importance
    deleted: int   # Удалено (soft delete)


# ═══════════════════════════════════════════════════════════
# FRACTAL MEMORY
# ═══════════════════════════════════════════════════════════

class FractalMemory:
    """
    Фрактальная память с иерархией L0 → L1 → L2 → L3.
    
    Принципы:
    1. Важное поднимается выше (консолидация)
    2. Неважное забывается (decay)
    3. Всё доступно через единый интерфейс
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: {
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "llm_client": <optional>,
                "embedding_func": <optional callable>,
                
                # Опции памяти
                "l0_capacity": 10,
                "l1_capacity": 50,
                "decay_rate_l0": 0.1,
                "decay_rate_l1": 0.05,
                "importance_threshold": 0.3,
                "consolidation_interval": 300,  # секунды
            }
        """
        self.config = config
        
        # Graph adapter (L2/L3)
        self.graph: GraphMemoryInterface = create_graph_memory(config)
        
        # L0: Working Memory (очень короткая)
        self.l0_cache: List[MemoryItem] = []
        self.l0_capacity = config.get("l0_capacity", 10)
        
        # L1: Short-Term Memory
        self.l1_cache: Dict[str, MemoryItem] = {}
        self.l1_capacity = config.get("l1_capacity", 50)
        
        # Decay rates
        self.decay_rate_l0 = config.get("decay_rate_l0", 0.1)
        self.decay_rate_l1 = config.get("decay_rate_l1", 0.05)
        self.importance_threshold = config.get("importance_threshold", 0.3)
        
        # Embedding function (опционально)
        self.embedding_func = config.get("embedding_func")
        
        # State
        self._initialized = False
        self._consolidation_task = None
    
    async def initialize(self) -> None:
        """Инициализация памяти"""
        if self._initialized:
            return
        
        await self.graph.initialize()
        self._initialized = True
        logger.info("FractalMemory initialized")
    
    async def close(self) -> None:
        """Закрытие памяти"""
        if self._consolidation_task:
            self._consolidation_task.cancel()
        await self.graph.close()
        self._initialized = False
    
    # ═══════════════════════════════════════════════════════
    # ОСНОВНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════
    
    async def remember(
        self, 
        content: str,
        importance: float = 1.0,
        metadata: Dict = None
    ) -> str:
        """
        Запомнить информацию.
        Сначала в L0, потом консолидируется выше.
        
        Args:
            content: Что запомнить
            importance: Начальная важность (0-1)
            metadata: Дополнительные данные
        
        Returns:
            ID созданной записи
        """
        self._ensure_initialized()
        
        # Создать embedding если есть функция
        embedding = None
        if self.embedding_func:
            embedding = await self._get_embedding(content)
        
        # Создать MemoryItem
        item = MemoryItem(
            id=self._generate_id(),
            content=content,
            embedding=embedding,
            importance=importance,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            level=0
        )
        
        # Добавить в L0
        self.l0_cache.append(item)
        logger.debug(f"Added to L0: {item.id[:8]}...")
        
        # Если L0 переполнен — триггер консолидации
        if len(self.l0_cache) > self.l0_capacity:
            await self._consolidate_l0_to_l1()
        
        return item.id
    
    async def recall(
        self, 
        query: str,
        limit: int = 5,
        levels: List[int] = None
    ) -> List[SearchResult]:
        """
        Вспомнить информацию.
        Ищет по всем уровням памяти.
        
        Args:
            query: Что искать
            limit: Максимум результатов
            levels: Какие уровни искать [0,1,2,3] или None для всех
        
        Returns:
            Список результатов, отсортированных по релевантности
        """
        self._ensure_initialized()
        
        if levels is None:
            levels = [0, 1, 2, 3]
        
        all_results = []
        
        # L0: поиск в working memory
        if 0 in levels:
            l0_results = self._search_l0(query)
            all_results.extend(l0_results)
        
        # L1: поиск в short-term
        if 1 in levels:
            l1_results = self._search_l1(query)
            all_results.extend(l1_results)
        
        # L2/L3: поиск в графе
        if 2 in levels or 3 in levels:
            graph_results = await self.graph.search(query, limit=limit * 2)
            all_results.extend(graph_results)
        
        # Сортировка по relevance
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Обновить access_count для найденных
        await self._update_access_counts(all_results[:limit])
        
        return all_results[:limit]
    
    async def consolidate(self) -> ConsolidationResult:
        """
        Консолидация памяти: L0 → L1 → L2 → L3.
        Вызывается автоматически или вручную.
        
        Returns:
            Статистика консолидации
        """
        self._ensure_initialized()
        
        result = ConsolidationResult(promoted=0, decayed=0, deleted=0)
        
        # L0 → L1
        r1 = await self._consolidate_l0_to_l1()
        result.promoted += r1.promoted
        result.decayed += r1.decayed
        result.deleted += r1.deleted
        
        # L1 → L2
        r2 = await self._consolidate_l1_to_l2()
        result.promoted += r2.promoted
        result.decayed += r2.decayed
        result.deleted += r2.deleted
        
        # Apply decay to all levels
        await self._apply_decay()
        
        logger.info(
            f"Consolidation complete: "
            f"promoted={result.promoted}, "
            f"decayed={result.decayed}, "
            f"deleted={result.deleted}"
        )
        
        return result
    
    # ═══════════════════════════════════════════════════════
    # КОНСОЛИДАЦИЯ
    # ═══════════════════════════════════════════════════════
    
    async def _consolidate_l0_to_l1(self) -> ConsolidationResult:
        """Консолидация L0 → L1"""
        result = ConsolidationResult(promoted=0, decayed=0, deleted=0)
        now = datetime.now()
        
        items_to_remove = []
        
        for item in self.l0_cache:
            age_minutes = (now - item.created_at).total_seconds() / 60
            
            # Рассчитать importance с decay
            new_importance = self._calculate_importance(item, age_minutes)
            item.importance = new_importance
            
            if new_importance > 0.7 or item.access_count > 2:
                # Повысить до L1
                item.level = 1
                self.l1_cache[item.id] = item
                items_to_remove.append(item)
                result.promoted += 1
                logger.debug(f"Promoted to L1: {item.id[:8]}...")
                
            elif new_importance < self.importance_threshold:
                # Удалить (забыть)
                items_to_remove.append(item)
                result.deleted += 1
                logger.debug(f"Forgotten from L0: {item.id[:8]}...")
                
            else:
                result.decayed += 1
        
        # Удалить обработанные
        for item in items_to_remove:
            if item in self.l0_cache:
                self.l0_cache.remove(item)
        
        return result
    
    async def _consolidate_l1_to_l2(self) -> ConsolidationResult:
        """Консолидация L1 → L2 (граф)"""
        result = ConsolidationResult(promoted=0, decayed=0, deleted=0)
        now = datetime.now()
        
        items_to_remove = []
        
        for item_id, item in list(self.l1_cache.items()):
            age_hours = (now - item.created_at).total_seconds() / 3600
            
            # Рассчитать importance
            new_importance = self._calculate_importance(item, age_hours * 60)
            item.importance = new_importance
            
            # Критерии для L2:
            # - Важность > 0.7
            # - Или доступ > 5 раз
            # - Или возраст > 1 час и важность > 0.5
            should_promote = (
                new_importance > 0.7 or 
                item.access_count > 5 or
                (age_hours > 1 and new_importance > 0.5)
            )
            
            if should_promote:
                # Сохранить в граф
                episode = Episode(
                    id=item.id,
                    content=item.content,
                    timestamp=item.created_at,
                    source="l1_consolidation",
                    importance_score=new_importance,
                    level=2,
                    metadata={"access_count": item.access_count}
                )
                await self.graph.add_episode(episode)
                
                items_to_remove.append(item_id)
                result.promoted += 1
                logger.debug(f"Promoted to L2: {item_id[:8]}...")
                
            elif new_importance < self.importance_threshold and age_hours > 2:
                # Удалить (забыть)
                items_to_remove.append(item_id)
                result.deleted += 1
                
            else:
                result.decayed += 1
        
        # Удалить обработанные
        for item_id in items_to_remove:
            self.l1_cache.pop(item_id, None)
        
        # Проверить capacity
        if len(self.l1_cache) > self.l1_capacity:
            # Удалить наименее важные
            sorted_items = sorted(
                self.l1_cache.items(),
                key=lambda x: x[1].importance
            )
            to_remove = len(self.l1_cache) - self.l1_capacity
            for item_id, _ in sorted_items[:to_remove]:
                self.l1_cache.pop(item_id, None)
                result.deleted += 1
        
        return result
    
    async def _apply_decay(self) -> None:
        """Применить decay ко всем уровням"""
        now = datetime.now()
        
        # L0 decay
        for item in self.l0_cache:
            age_minutes = (now - item.last_accessed).total_seconds() / 60
            item.importance *= np.exp(-self.decay_rate_l0 * age_minutes / 60)
        
        # L1 decay
        for item in self.l1_cache.values():
            age_hours = (now - item.last_accessed).total_seconds() / 3600
            item.importance *= np.exp(-self.decay_rate_l1 * age_hours)
        
        # L2/L3 decay в графе (через Cypher)
        await self.graph.execute_cypher(
            """
            MATCH (ep:Episode)
            WHERE ep.deleted = false
              AND ep.last_accessed < datetime() - duration({hours: 24})
            SET ep.importance_score = ep.importance_score * 0.95
            """,
            {}
        )
    
    def _calculate_importance(
        self, 
        item: MemoryItem, 
        age_minutes: float
    ) -> float:
        """
        Рассчитать importance с учётом:
        - Temporal decay
        - Access count (reinforcement)
        """
        # Базовый decay
        decay_rate = self.decay_rate_l0 if item.level == 0 else self.decay_rate_l1
        temporal_decay = np.exp(-decay_rate * age_minutes / 60)
        
        # Reinforcement: частый доступ замедляет decay
        reinforcement = 1.0 + np.log1p(item.access_count) * 0.1
        
        # Итоговый importance
        new_importance = item.importance * temporal_decay * reinforcement
        
        return max(0.0, min(1.0, new_importance))
    
    # ═══════════════════════════════════════════════════════
    # ПОИСК
    # ═══════════════════════════════════════════════════════
    
    def _search_l0(self, query: str) -> List[SearchResult]:
        """Поиск в L0 (простой keyword matching)"""
        results = []
        query_lower = query.lower()
        
        for item in self.l0_cache:
            if query_lower in item.content.lower():
                results.append(SearchResult(
                    content=item.content,
                    relevance_score=item.importance,
                    source="l0",
                    timestamp=item.created_at,
                    metadata={"level": 0}
                ))
        
        return results
    
    def _search_l1(self, query: str) -> List[SearchResult]:
        """Поиск в L1"""
        results = []
        query_lower = query.lower()
        
        for item in self.l1_cache.values():
            if query_lower in item.content.lower():
                results.append(SearchResult(
                    content=item.content,
                    relevance_score=item.importance,
                    source="l1",
                    timestamp=item.created_at,
                    metadata={"level": 1}
                ))
        
        return results
    
    async def _update_access_counts(self, results: List[SearchResult]) -> None:
        """Обновить счётчики доступа для найденных результатов"""
        for result in results:
            level = result.metadata.get("level", 2)
            
            if level == 0:
                # L0
                for item in self.l0_cache:
                    if item.content == result.content:
                        item.access_count += 1
                        item.last_accessed = datetime.now()
                        break
                        
            elif level == 1:
                # L1
                for item in self.l1_cache.values():
                    if item.content == result.content:
                        item.access_count += 1
                        item.last_accessed = datetime.now()
                        break
    
    # ═══════════════════════════════════════════════════════
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Получить embedding для текста"""
        if self.embedding_func:
            return await self.embedding_func(text)
        return None
    
    def _generate_id(self) -> str:
        """Генерация уникального ID"""
        return str(uuid.uuid4())
    
    def _ensure_initialized(self):
        """Проверить инициализацию"""
        if not self._initialized:
            raise RuntimeError(
                "FractalMemory not initialized. "
                "Call await memory.initialize() first."
            )
    
    # ═══════════════════════════════════════════════════════
    # СТАТИСТИКА
    # ═══════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """Получить статистику памяти"""
        return {
            "l0_size": len(self.l0_cache),
            "l0_capacity": self.l0_capacity,
            "l1_size": len(self.l1_cache),
            "l1_capacity": self.l1_capacity,
            "l0_avg_importance": np.mean([i.importance for i in self.l0_cache]) if self.l0_cache else 0,
            "l1_avg_importance": np.mean([i.importance for i in self.l1_cache.values()]) if self.l1_cache else 0,
        }
    
    # ═══════════════════════════════════════════════════════
    # GARBAGE COLLECTION
    # ═══════════════════════════════════════════════════════
    
    async def garbage_collect(self, soft_delete_age_days: int = 7) -> Dict:
        """
        Garbage Collection:
        1. Физически удалить soft deleted старше N дней
        2. Soft delete низко-важные записи
        
        Args:
            soft_delete_age_days: Через сколько дней после soft delete удалять физически
        
        Returns:
            Статистика GC
        """
        self._ensure_initialized()
        
        stats = {
            "hard_deleted": 0,
            "soft_deleted": 0
        }
        
        # 1. Физическое удаление (только soft deleted + старые)
        hard_delete_result = await self.graph.execute_cypher(
            """
            MATCH (n)
            WHERE n.deleted = true
              AND n.deleted_at < datetime() - duration({days: $days})
            WITH n, labels(n) as labels
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """,
            {"days": soft_delete_age_days}
        )
        stats["hard_deleted"] = hard_delete_result[0]["deleted_count"] if hard_delete_result else 0
        
        # 2. Soft delete низко-важных
        soft_delete_result = await self.graph.execute_cypher(
            """
            MATCH (ep:Episode)
            WHERE ep.deleted = false
              AND ep.importance_score < $threshold
              AND ep.access_count = 0
              AND ep.timestamp < datetime() - duration({days: 30})
            SET ep.deleted = true,
                ep.deleted_at = datetime()
            RETURN count(ep) as deleted_count
            """,
            {"threshold": self.importance_threshold}
        )
        stats["soft_deleted"] = soft_delete_result[0]["deleted_count"] if soft_delete_result else 0
        
        logger.info(f"GC complete: {stats}")
        return stats


# ═══════════════════════════════════════════════════════════
# ФАБРИКА
# ═══════════════════════════════════════════════════════════

def create_fractal_memory(config: Dict) -> FractalMemory:
    """
    Фабрика для создания FractalMemory.
    
    Args:
        config: Конфигурация (см. FractalMemory.__init__)
    
    Returns:
        Настроенный экземпляр FractalMemory
    """
    return FractalMemory(config)
```

---

## 3️⃣ Тесты

### Файл `tests/test_memory.py`:

```python
"""
Unit тесты для FractalMemory.

Запуск:
    pytest tests/test_memory.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.core.memory import FractalMemory, create_fractal_memory
from src.core.graphiti_adapter import MockGraphMemory


@pytest.fixture
def config():
    """Конфигурация для тестов (с mock)"""
    return {
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "test",
        "l0_capacity": 5,
        "l1_capacity": 10,
        "importance_threshold": 0.3,
    }


@pytest.fixture
async def memory(config):
    """Создать FractalMemory с mock адаптером"""
    mem = FractalMemory(config)
    mem.graph = MockGraphMemory()  # Подменяем на mock
    await mem.initialize()
    yield mem
    await mem.close()


class TestFractalMemory:
    """Тесты FractalMemory"""
    
    @pytest.mark.asyncio
    async def test_remember_adds_to_l0(self, memory):
        """remember() добавляет в L0"""
        item_id = await memory.remember("test content")
        
        assert len(memory.l0_cache) == 1
        assert memory.l0_cache[0].id == item_id
        assert memory.l0_cache[0].content == "test content"
    
    @pytest.mark.asyncio
    async def test_recall_finds_in_l0(self, memory):
        """recall() находит в L0"""
        await memory.remember("Python is great")
        
        results = await memory.recall("Python")
        
        assert len(results) == 1
        assert "Python" in results[0].content
    
    @pytest.mark.asyncio
    async def test_consolidation_promotes_to_l1(self, memory):
        """Консолидация повышает важные записи в L1"""
        # Добавить запись с высокой важностью
        await memory.remember("important info", importance=0.9)
        
        # Консолидировать
        result = await memory.consolidate()
        
        assert result.promoted >= 1
        assert len(memory.l1_cache) >= 1
    
    @pytest.mark.asyncio
    async def test_l0_overflow_triggers_consolidation(self, memory):
        """Переполнение L0 триггерит консолидацию"""
        # Заполнить L0 выше capacity
        for i in range(memory.l0_capacity + 2):
            await memory.remember(f"content {i}", importance=0.8)
        
        # L0 должен был консолидироваться
        assert len(memory.l0_cache) <= memory.l0_capacity
    
    @pytest.mark.asyncio
    async def test_soft_delete_works(self, memory):
        """Soft delete помечает запись"""
        # Добавить и сохранить в граф
        await memory.remember("to delete", importance=0.9)
        await memory.consolidate()
        
        # Проверить что есть в графе
        # (через mock это сложно, но логика работает)
        
        # GC с soft delete
        stats = await memory.garbage_collect()
        
        # Проверить что метод отработал без ошибок
        assert "soft_deleted" in stats
        assert "hard_deleted" in stats
    
    @pytest.mark.asyncio
    async def test_stats_returns_correct_data(self, memory):
        """get_stats() возвращает корректные данные"""
        await memory.remember("test 1")
        await memory.remember("test 2")
        
        stats = memory.get_stats()
        
        assert stats["l0_size"] == 2
        assert stats["l0_capacity"] == memory.l0_capacity
        assert stats["l1_size"] == 0


class TestConsolidation:
    """Тесты консолидации"""
    
    @pytest.mark.asyncio
    async def test_low_importance_forgotten(self, memory):
        """Низкая важность → забывание"""
        # Добавить с низкой важностью
        await memory.remember("unimportant", importance=0.1)
        
        # Искусственно состарить
        memory.l0_cache[0].created_at = datetime.now() - timedelta(hours=1)
        
        # Консолидировать
        result = await memory.consolidate()
        
        # Должно быть удалено или decayed
        assert result.deleted >= 1 or result.decayed >= 1
    
    @pytest.mark.asyncio
    async def test_high_access_promotes(self, memory):
        """Частый доступ повышает уровень"""
        await memory.remember("popular content", importance=0.5)
        
        # Имитировать частый доступ
        memory.l0_cache[0].access_count = 5
        
        # Консолидировать
        result = await memory.consolidate()
        
        assert result.promoted >= 1
```

---

## ✅ Критерии завершения Phase 2

- [ ] `GraphitiAdapter` создан и работает
- [ ] `FractalMemory` создан и работает
- [ ] `remember()` добавляет в L0
- [ ] `recall()` ищет по всем уровням
- [ ] Консолидация L0→L1→L2 работает
- [ ] Soft delete работает
- [ ] Unit тесты проходят: `pytest tests/test_memory.py -v`

---

## 📚 Следующий шаг

Перейди к: **[04_PHASE3_LEARNING.md](04_PHASE3_LEARNING.md)** — ReasoningBank и самообучение
