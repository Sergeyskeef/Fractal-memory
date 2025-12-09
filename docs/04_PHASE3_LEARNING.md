# 04. Phase 3: Самообучение (ReasoningBank)

## 🎯 Цель

Реализовать систему обучения на успехах и ошибках.

**Время**: 2-3 дня  
**Результат**: Агент учится из опыта и избегает повторения ошибок

---

## 📋 Чек-лист Phase 3

- [ ] ReasoningBank создан
- [ ] Experience logging работает
- [ ] Strategy extraction работает
- [ ] Negative reinforcement работает
- [ ] Интеграция с агентом
- [ ] Тесты проходят

---

## 🧠 Концепция самообучения

```
┌─────────────────────────────────────────────────────────┐
│                   ЦИКЛ ОБУЧЕНИЯ                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   1. RETRIEVE                                           │
│      └─ Найти похожие задачи в памяти                  │
│      └─ Получить стратегии (успешные и провальные)     │
│                                                         │
│   2. EXECUTE                                            │
│      └─ Выполнить задачу с учётом стратегий            │
│                                                         │
│   3. JUDGE                                              │
│      └─ Оценить результат (успех/провал)               │
│                                                         │
│   4. LEARN                                              │
│      └─ Сохранить опыт                                 │
│      └─ Обновить confidence стратегий                  │
│      └─ Извлечь новые паттерны                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 1️⃣ ReasoningBank

### Файл `src/core/learning.py`:

```python
"""
ReasoningBank — система самообучения на опыте.

Ключевые возможности:
1. Сохранение опыта (успехи и неудачи)
2. Извлечение стратегий из опыта
3. Negative reinforcement (обучение на ошибках)
4. Strategy selection (выбор лучшей стратегии)

Использование:
    bank = ReasoningBank(graph_memory)
    
    # Записать опыт
    await bank.log_experience(task, action, outcome)
    
    # Найти стратегии
    strategies = await bank.get_strategies_for_task(task)
    
    # Обновить после результата
    await bank.update_strategy_feedback(strategy_id, outcome)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
import logging
import json
import uuid
import numpy as np

from .graphiti_adapter import GraphMemoryInterface, Episode

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# МОДЕЛИ
# ═══════════════════════════════════════════════════════════

class Outcome(Enum):
    """Результат выполнения задачи"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class Experience:
    """Записанный опыт"""
    id: str
    task_description: str
    task_type: str
    context: Dict
    action_taken: str
    outcome: Outcome
    reasoning: str
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Strategy:
    """Извлечённая стратегия"""
    id: str
    description: str
    task_types: List[str]  # Для каких задач применима
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Процент успеха"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Нет данных → нейтральная оценка
        return self.success_count / total
    
    @property
    def total_uses(self) -> int:
        """Всего использований"""
        return self.success_count + self.failure_count
    
    def to_dict(self) -> Dict:
        """Сериализация в dict"""
        return {
            "id": self.id,
            "description": self.description,
            "task_types": self.task_types,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "success_rate": self.success_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Strategy":
        """Десериализация из dict"""
        return cls(
            id=data["id"],
            description=data["description"],
            task_types=data.get("task_types", []),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            confidence=data.get("confidence", 0.5),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None
        )


# ═══════════════════════════════════════════════════════════
# REASONING BANK
# ═══════════════════════════════════════════════════════════

class ReasoningBank:
    """
    Банк стратегий и опыта для самообучения.
    """
    
    def __init__(
        self, 
        graph: GraphMemoryInterface,
        config: Dict = None
    ):
        """
        Args:
            graph: GraphMemory для хранения
            config: {
                "experience_buffer_size": 100,
                "min_experiences_for_strategy": 3,
                "confidence_boost": 0.05,
                "confidence_penalty": 0.1,
                "exploration_rate": 0.1
            }
        """
        self.graph = graph
        self.config = config or {}
        
        # Буфер опыта (до извлечения стратегий)
        self.experience_buffer: List[Experience] = []
        self.buffer_size = self.config.get("experience_buffer_size", 100)
        
        # Кэш стратегий
        self.strategies_cache: Dict[str, Strategy] = {}
        
        # Параметры reinforcement
        self.confidence_boost = self.config.get("confidence_boost", 0.05)
        self.confidence_penalty = self.config.get("confidence_penalty", 0.1)
        self.exploration_rate = self.config.get("exploration_rate", 0.1)
        self.min_experiences = self.config.get("min_experiences_for_strategy", 3)
    
    # ═══════════════════════════════════════════════════════
    # LOGGING EXPERIENCE
    # ═══════════════════════════════════════════════════════
    
    async def log_experience(
        self,
        task_description: str,
        task_type: str,
        context: Dict,
        action_taken: str,
        outcome: Outcome,
        reasoning: str,
        error_message: Optional[str] = None
    ) -> str:
        """
        Записать опыт выполнения задачи.
        
        Args:
            task_description: Описание задачи
            task_type: Тип задачи (для группировки)
            context: Контекст выполнения
            action_taken: Что было сделано
            outcome: Результат
            reasoning: Почему так сделали
            error_message: Сообщение об ошибке (если failure)
        
        Returns:
            ID записанного опыта
        """
        experience = Experience(
            id=str(uuid.uuid4()),
            task_description=task_description,
            task_type=task_type,
            context=context,
            action_taken=action_taken,
            outcome=outcome,
            reasoning=reasoning,
            error_message=error_message,
            timestamp=datetime.now()
        )
        
        # Добавить в буфер
        self.experience_buffer.append(experience)
        
        # Сохранить в граф
        episode = Episode(
            id=f"exp_{experience.id}",
            content=json.dumps({
                "type": "experience",
                "task_type": task_type,
                "task_description": task_description,
                "action": action_taken,
                "outcome": outcome.value,
                "reasoning": reasoning,
                "error": error_message
            }),
            timestamp=experience.timestamp,
            source="experience_log",
            outcome=outcome.value,
            importance_score=1.0 if outcome == Outcome.FAILURE else 0.8
        )
        await self.graph.add_episode(episode)
        
        logger.info(
            f"Experience logged: {task_type} -> {outcome.value}"
        )
        
        # Если буфер полон — извлечь стратегии
        if len(self.experience_buffer) >= self.buffer_size:
            await self.extract_strategies()
        
        return experience.id
    
    # ═══════════════════════════════════════════════════════
    # STRATEGY EXTRACTION
    # ═══════════════════════════════════════════════════════
    
    async def extract_strategies(self) -> List[Strategy]:
        """
        Извлечь стратегии из накопленного опыта.
        Группирует по task_type и находит паттерны.
        
        Returns:
            Список новых стратегий
        """
        if not self.experience_buffer:
            return []
        
        # Группировать по task_type
        by_task_type: Dict[str, List[Experience]] = {}
        for exp in self.experience_buffer:
            if exp.task_type not in by_task_type:
                by_task_type[exp.task_type] = []
            by_task_type[exp.task_type].append(exp)
        
        new_strategies = []
        
        for task_type, experiences in by_task_type.items():
            # Нужно минимум N опытов
            if len(experiences) < self.min_experiences:
                continue
            
            # Разделить на успешные и неудачные
            successes = [e for e in experiences if e.outcome == Outcome.SUCCESS]
            failures = [e for e in experiences if e.outcome == Outcome.FAILURE]
            
            # Извлечь стратегию из успехов
            if len(successes) >= 2:
                strategy = self._extract_from_successes(task_type, successes)
                if strategy:
                    new_strategies.append(strategy)
                    await self._save_strategy(strategy)
            
            # Извлечь anti-pattern из неудач
            if len(failures) >= 2:
                anti_strategy = self._extract_from_failures(task_type, failures)
                if anti_strategy:
                    new_strategies.append(anti_strategy)
                    await self._save_strategy(anti_strategy)
        
        # Очистить обработанные
        self.experience_buffer.clear()
        
        logger.info(f"Extracted {len(new_strategies)} strategies")
        return new_strategies
    
    def _extract_from_successes(
        self, 
        task_type: str, 
        successes: List[Experience]
    ) -> Optional[Strategy]:
        """Извлечь паттерн успеха"""
        # Найти общие элементы в actions
        actions = [e.action_taken for e in successes]
        common_words = self._find_common_keywords(actions)
        
        if not common_words:
            return None
        
        description = f"For {task_type}: {', '.join(common_words[:5])}"
        
        strategy = Strategy(
            id=str(uuid.uuid4()),
            description=description,
            task_types=[task_type],
            success_count=len(successes),
            failure_count=0,
            confidence=min(0.9, 0.5 + len(successes) * 0.1),
            metadata={"source": "success_extraction"}
        )
        
        self.strategies_cache[strategy.id] = strategy
        return strategy
    
    def _extract_from_failures(
        self, 
        task_type: str, 
        failures: List[Experience]
    ) -> Optional[Strategy]:
        """Извлечь anti-pattern (что НЕ делать)"""
        # Найти общие элементы в actions
        actions = [e.action_taken for e in failures]
        common_words = self._find_common_keywords(actions)
        
        if not common_words:
            return None
        
        description = f"AVOID for {task_type}: {', '.join(common_words[:5])}"
        
        strategy = Strategy(
            id=str(uuid.uuid4()),
            description=description,
            task_types=[task_type],
            success_count=0,
            failure_count=len(failures),
            confidence=0.1,  # Низкий confidence = НЕ использовать
            metadata={
                "source": "failure_extraction",
                "is_anti_pattern": True
            }
        )
        
        self.strategies_cache[strategy.id] = strategy
        return strategy
    
    def _find_common_keywords(self, texts: List[str]) -> List[str]:
        """Найти общие ключевые слова"""
        if not texts:
            return []
        
        # Простая версия: частотный анализ
        word_counts: Dict[str, int] = {}
        
        for text in texts:
            words = set(text.lower().split())
            for word in words:
                if len(word) > 3:  # Игнорировать короткие
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Слова, встречающиеся в >50% текстов
        threshold = len(texts) // 2
        common = [
            word for word, count in word_counts.items()
            if count > threshold
        ]
        
        return sorted(common, key=lambda w: word_counts[w], reverse=True)
    
    async def _save_strategy(self, strategy: Strategy) -> None:
        """Сохранить стратегию в граф"""
        episode = Episode(
            id=f"strategy_{strategy.id}",
            content=json.dumps(strategy.to_dict()),
            timestamp=strategy.created_at,
            source="strategy_extraction",
            importance_score=strategy.confidence,
            metadata={"type": "strategy"}
        )
        await self.graph.add_episode(episode)
    
    # ═══════════════════════════════════════════════════════
    # STRATEGY RETRIEVAL
    # ═══════════════════════════════════════════════════════
    
    async def get_strategies_for_task(
        self,
        task_description: str,
        task_type: str = None,
        limit: int = 5
    ) -> List[Strategy]:
        """
        Найти подходящие стратегии для задачи.
        
        Args:
            task_description: Описание задачи
            task_type: Тип задачи (опционально)
            limit: Максимум стратегий
        
        Returns:
            Список стратегий, отсортированных по релевантности
        """
        # Поиск в графе
        query = f"strategy {task_type or ''} {task_description}"
        results = await self.graph.search(query, limit=limit * 2)
        
        strategies = []
        for result in results:
            try:
                data = json.loads(result.content)
                if data.get("type") == "strategy" or "description" in data:
                    strategy = Strategy.from_dict(data)
                    
                    # Фильтр anti-patterns с низким confidence
                    if strategy.confidence < 0.2:
                        # Это anti-pattern, пометить
                        strategy.metadata["is_anti_pattern"] = True
                    
                    strategies.append(strategy)
            except:
                continue
        
        # Сортировка: высокий confidence первый
        strategies.sort(key=lambda s: s.confidence, reverse=True)
        
        return strategies[:limit]
    
    async def select_best_strategy(
        self,
        task_description: str,
        task_type: str = None,
        context: Dict = None
    ) -> Optional[Strategy]:
        """
        Выбрать лучшую стратегию с учётом exploration.
        
        Uses epsilon-greedy:
        - С вероятностью epsilon → случайная стратегия (exploration)
        - Иначе → лучшая по confidence (exploitation)
        
        Returns:
            Лучшая стратегия или None
        """
        strategies = await self.get_strategies_for_task(
            task_description, 
            task_type
        )
        
        if not strategies:
            return None
        
        # Фильтруем anti-patterns
        good_strategies = [
            s for s in strategies 
            if not s.metadata.get("is_anti_pattern", False)
        ]
        
        if not good_strategies:
            return None
        
        # Epsilon-greedy selection
        if np.random.random() < self.exploration_rate:
            # Exploration: случайный выбор
            selected = np.random.choice(good_strategies)
            logger.debug(f"Strategy selection: EXPLORATION -> {selected.id[:8]}")
        else:
            # Exploitation: лучший по confidence
            selected = max(good_strategies, key=lambda s: s.confidence)
            logger.debug(f"Strategy selection: EXPLOITATION -> {selected.id[:8]}")
        
        return selected
    
    # ═══════════════════════════════════════════════════════
    # FEEDBACK & REINFORCEMENT
    # ═══════════════════════════════════════════════════════
    
    async def update_strategy_feedback(
        self,
        strategy_id: str,
        outcome: Outcome
    ) -> bool:
        """
        Обновить стратегию на основе результата.
        
        Positive reinforcement: успех → повысить confidence
        Negative reinforcement: неудача → понизить confidence
        
        Args:
            strategy_id: ID стратегии
            outcome: Результат применения
        
        Returns:
            True если обновлено
        """
        # Найти стратегию
        strategy = self.strategies_cache.get(strategy_id)
        
        if not strategy:
            # Поиск в графе
            results = await self.graph.search(
                f"strategy_{strategy_id}",
                limit=1
            )
            if results:
                try:
                    data = json.loads(results[0].content)
                    strategy = Strategy.from_dict(data)
                    self.strategies_cache[strategy_id] = strategy
                except:
                    return False
        
        if not strategy:
            logger.warning(f"Strategy not found: {strategy_id}")
            return False
        
        # Обновить счётчики
        if outcome == Outcome.SUCCESS:
            strategy.success_count += 1
            # Positive reinforcement
            strategy.confidence = min(
                1.0, 
                strategy.confidence + self.confidence_boost
            )
            logger.info(
                f"Strategy {strategy_id[:8]} SUCCESS: "
                f"confidence={strategy.confidence:.2f}"
            )
            
        elif outcome == Outcome.FAILURE:
            strategy.failure_count += 1
            # Negative reinforcement
            strategy.confidence = max(
                0.0,
                strategy.confidence - self.confidence_penalty
            )
            
            # Усиливать penalty при частых неудачах
            if strategy.failure_count > 5:
                strategy.confidence = max(
                    0.0,
                    strategy.confidence - self.confidence_penalty
                )
            
            logger.info(
                f"Strategy {strategy_id[:8]} FAILURE: "
                f"confidence={strategy.confidence:.2f}"
            )
        
        strategy.last_used = datetime.now()
        
        # Сохранить обновление
        await self._save_strategy(strategy)
        
        return True
    
    # ═══════════════════════════════════════════════════════
    # ANTI-PATTERNS
    # ═══════════════════════════════════════════════════════
    
    async def get_anti_patterns(
        self,
        task_type: str = None,
        limit: int = 5
    ) -> List[Strategy]:
        """
        Получить список anti-patterns (что НЕ делать).
        
        Returns:
            Стратегии с низким confidence (неудачные подходы)
        """
        query = f"AVOID anti-pattern {task_type or ''}"
        results = await self.graph.search(query, limit=limit * 2)
        
        anti_patterns = []
        for result in results:
            try:
                data = json.loads(result.content)
                strategy = Strategy.from_dict(data)
                
                # Только с низким confidence или помеченные
                if (strategy.confidence < 0.3 or 
                    strategy.metadata.get("is_anti_pattern")):
                    anti_patterns.append(strategy)
            except:
                continue
        
        return anti_patterns[:limit]
    
    # ═══════════════════════════════════════════════════════
    # СТАТИСТИКА
    # ═══════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            "experience_buffer_size": len(self.experience_buffer),
            "strategies_cached": len(self.strategies_cache),
            "exploration_rate": self.exploration_rate,
            "avg_confidence": np.mean([
                s.confidence for s in self.strategies_cache.values()
            ]) if self.strategies_cache else 0
        }


# ═══════════════════════════════════════════════════════════
# SELF-LEARNING AGENT MIXIN
# ═══════════════════════════════════════════════════════════

class SelfLearningMixin:
    """
    Mixin для добавления самообучения к агенту.
    
    Использование:
        class MyAgent(SelfLearningMixin):
            def __init__(self, reasoning_bank):
                self.reasoning_bank = reasoning_bank
            
            async def execute_task(self, task):
                return await self.execute_with_learning(task, self._do_task)
    """
    
    reasoning_bank: ReasoningBank
    
    async def execute_with_learning(
        self,
        task_description: str,
        task_type: str,
        execute_func,
        context: Dict = None
    ):
        """
        Выполнить задачу с циклом обучения.
        
        Args:
            task_description: Описание задачи
            task_type: Тип задачи
            execute_func: Функция выполнения (async callable)
            context: Контекст
        
        Returns:
            Результат выполнения
        """
        context = context or {}
        
        # 1. RETRIEVE: Найти стратегию
        strategy = await self.reasoning_bank.select_best_strategy(
            task_description,
            task_type,
            context
        )
        
        # 2. PLAN: Подготовить план
        if strategy:
            plan = f"Using strategy: {strategy.description}"
            context["strategy_id"] = strategy.id
        else:
            plan = "No prior strategy, using default approach"
        
        # 3. EXECUTE
        outcome = Outcome.UNKNOWN
        error_message = None
        result = None
        
        try:
            result = await execute_func(task_description, context)
            outcome = Outcome.SUCCESS
            
        except Exception as e:
            outcome = Outcome.FAILURE
            error_message = str(e)
            logger.error(f"Task failed: {e}")
        
        # 4. LEARN: Записать опыт
        await self.reasoning_bank.log_experience(
            task_description=task_description,
            task_type=task_type,
            context=context,
            action_taken=plan,
            outcome=outcome,
            reasoning=f"Executed with strategy: {strategy.id if strategy else 'none'}",
            error_message=error_message
        )
        
        # 5. UPDATE: Обновить стратегию
        if strategy:
            await self.reasoning_bank.update_strategy_feedback(
                strategy.id,
                outcome
            )
        
        return result
```

---

## 2️⃣ Интеграция с агентом

### Файл `src/agent.py` (обновление):

```python
"""
Агент с самообучением.
"""

from .core.memory import FractalMemory
from .core.learning import ReasoningBank, SelfLearningMixin, Outcome


class AutonomousAgent(SelfLearningMixin):
    """
    Автономный агент с памятью и самообучением.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Инициализация памяти
        self.memory = FractalMemory(config)
        
        # Инициализация обучения
        self.reasoning_bank = ReasoningBank(
            self.memory.graph,
            config.get("learning_config", {})
        )
        
        # LLM client
        self.llm = config.get("llm_client")
    
    async def initialize(self):
        """Инициализация"""
        await self.memory.initialize()
    
    async def chat(self, message: str) -> str:
        """
        Обработка сообщения с запоминанием.
        """
        # Запомнить сообщение
        await self.memory.remember(message)
        
        # Найти релевантный контекст
        context = await self.memory.recall(message)
        
        # Найти стратегии (если это задача)
        strategies = []
        if self._is_task(message):
            strategies = await self.reasoning_bank.get_strategies_for_task(
                message,
                task_type=self._detect_task_type(message)
            )
        
        # Генерация ответа
        response = await self._generate_response(
            message, 
            context, 
            strategies
        )
        
        # Запомнить ответ
        await self.memory.remember(response)
        
        return response
    
    async def execute_task(
        self, 
        task: str, 
        task_type: str = "general"
    ):
        """
        Выполнить задачу с обучением.
        """
        return await self.execute_with_learning(
            task_description=task,
            task_type=task_type,
            execute_func=self._do_task,
            context={}
        )
    
    async def _do_task(self, task: str, context: Dict):
        """Реальное выполнение задачи"""
        # Здесь твоя логика выполнения
        pass
    
    async def _generate_response(
        self, 
        message: str, 
        context: List,
        strategies: List
    ) -> str:
        """Генерация ответа через LLM"""
        # Построить промпт с контекстом и стратегиями
        prompt = self._build_prompt(message, context, strategies)
        
        if self.llm:
            return await self.llm.complete(prompt)
        else:
            return "LLM not configured"
    
    def _is_task(self, message: str) -> bool:
        """Проверить является ли сообщение задачей"""
        task_keywords = ["сделай", "создай", "напиши", "исправь", "do", "create", "write", "fix"]
        return any(kw in message.lower() for kw in task_keywords)
    
    def _detect_task_type(self, message: str) -> str:
        """Определить тип задачи"""
        if "код" in message.lower() or "code" in message.lower():
            return "coding"
        elif "документ" in message.lower() or "doc" in message.lower():
            return "documentation"
        elif "анализ" in message.lower() or "analysis" in message.lower():
            return "analysis"
        return "general"
    
    def _build_prompt(
        self, 
        message: str, 
        context: List,
        strategies: List
    ) -> str:
        """Построить промпт"""
        parts = [f"User: {message}"]
        
        if context:
            parts.append("\nRelevant context:")
            for c in context[:3]:
                parts.append(f"- {c.content[:200]}")
        
        if strategies:
            parts.append("\nApplicable strategies:")
            for s in strategies[:2]:
                if s.confidence > 0.5:
                    parts.append(f"- DO: {s.description}")
                else:
                    parts.append(f"- AVOID: {s.description}")
        
        return "\n".join(parts)
```

---

## 3️⃣ Тесты

### Файл `tests/test_learning.py`:

```python
"""
Тесты ReasoningBank.
"""

import pytest
from datetime import datetime
from src.core.learning import (
    ReasoningBank, 
    Strategy, 
    Experience, 
    Outcome
)
from src.core.graphiti_adapter import MockGraphMemory


@pytest.fixture
async def reasoning_bank():
    """Создать ReasoningBank с mock"""
    graph = MockGraphMemory()
    await graph.initialize()
    
    bank = ReasoningBank(graph, {
        "min_experiences_for_strategy": 2,
        "exploration_rate": 0.1
    })
    
    return bank


class TestReasoningBank:
    
    @pytest.mark.asyncio
    async def test_log_experience(self, reasoning_bank):
        """log_experience записывает опыт"""
        exp_id = await reasoning_bank.log_experience(
            task_description="Test task",
            task_type="testing",
            context={"key": "value"},
            action_taken="Did something",
            outcome=Outcome.SUCCESS,
            reasoning="Because"
        )
        
        assert exp_id is not None
        assert len(reasoning_bank.experience_buffer) == 1
    
    @pytest.mark.asyncio
    async def test_strategy_extraction(self, reasoning_bank):
        """extract_strategies извлекает паттерны"""
        # Добавить несколько успешных опытов
        for i in range(3):
            await reasoning_bank.log_experience(
                task_description=f"Task {i}",
                task_type="coding",
                context={},
                action_taken="Use Python and tests",
                outcome=Outcome.SUCCESS,
                reasoning="Standard approach"
            )
        
        # Извлечь стратегии
        strategies = await reasoning_bank.extract_strategies()
        
        assert len(strategies) >= 1
    
    @pytest.mark.asyncio
    async def test_negative_reinforcement(self, reasoning_bank):
        """Неудачи снижают confidence"""
        # Создать стратегию
        strategy = Strategy(
            id="test-strategy",
            description="Test strategy",
            task_types=["testing"],
            confidence=0.8
        )
        reasoning_bank.strategies_cache[strategy.id] = strategy
        await reasoning_bank._save_strategy(strategy)
        
        # Обновить с неудачей
        await reasoning_bank.update_strategy_feedback(
            strategy.id,
            Outcome.FAILURE
        )
        
        # Confidence должен снизиться
        updated = reasoning_bank.strategies_cache[strategy.id]
        assert updated.confidence < 0.8
        assert updated.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_positive_reinforcement(self, reasoning_bank):
        """Успехи повышают confidence"""
        strategy = Strategy(
            id="test-strategy-2",
            description="Test strategy 2",
            task_types=["testing"],
            confidence=0.5
        )
        reasoning_bank.strategies_cache[strategy.id] = strategy
        await reasoning_bank._save_strategy(strategy)
        
        # Обновить с успехом
        await reasoning_bank.update_strategy_feedback(
            strategy.id,
            Outcome.SUCCESS
        )
        
        updated = reasoning_bank.strategies_cache[strategy.id]
        assert updated.confidence > 0.5
        assert updated.success_count == 1


class TestStrategy:
    
    def test_success_rate(self):
        """success_rate считается правильно"""
        strategy = Strategy(
            id="test",
            description="Test",
            task_types=[],
            success_count=7,
            failure_count=3
        )
        
        assert strategy.success_rate == 0.7
    
    def test_serialization(self):
        """to_dict/from_dict работают"""
        original = Strategy(
            id="test",
            description="Test strategy",
            task_types=["a", "b"],
            success_count=5,
            failure_count=2,
            confidence=0.75
        )
        
        data = original.to_dict()
        restored = Strategy.from_dict(data)
        
        assert restored.id == original.id
        assert restored.description == original.description
        assert restored.success_count == original.success_count
```

---

## ✅ Критерии завершения Phase 3

- [ ] `ReasoningBank` создан
- [ ] `log_experience()` записывает опыт
- [ ] `extract_strategies()` извлекает паттерны
- [ ] `update_strategy_feedback()` обновляет confidence
- [ ] Negative reinforcement работает (неудачи снижают confidence)
- [ ] Интеграция с агентом работает
- [ ] Тесты проходят: `pytest tests/test_learning.py -v`

---

## 📚 Следующий шаг

Перейди к: **[05_PHASE4_PRODUCTION.md](05_PHASE4_PRODUCTION.md)** — мониторинг и production
