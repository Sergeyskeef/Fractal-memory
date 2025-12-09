# 01. Архитектура системы

## 🎯 Цель документа

Объяснить **как работает система** на высоком уровне. Прочитай это первым, прежде чем писать код.

---

## 📊 Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                         АГЕНТ                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              FractalMemory (твой код)                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │  │   L0    │  │   L1    │  │   L2    │  │   L3    │ │   │
│  │  │  STM    │→ │  MTM    │→ │ Episodes│→ │   LTM   │ │   │
│  │  │(память) │  │(кэш)    │  │ (граф)  │  │ (граф)  │ │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │           GraphitiAdapter (обёртка)                  │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐     ┌─────▼─────┐    ┌─────▼─────┐
    │  Neo4j  │     │   Redis   │    │    LLM    │
    │ (граф)  │     │(события)  │    │ (OpenAI)  │
    └─────────┘     └───────────┘    └───────────┘
```

---

## 🧠 Ключевые концепции

### 1. Фрактальная иерархия памяти (L0 → L3)

Память организована в 4 уровня, как у человека:

| Уровень | Название | Где хранится | Время жизни | Что хранит |
|---------|----------|--------------|-------------|------------|
| **L0** | Working Memory | Python list | Секунды-минуты | Текущий контекст разговора |
| **L1** | Short-Term | Python dict | Минуты-часы | Текущая сессия |
| **L2** | Medium-Term | Redis/SQLite | Дни-недели | Консолидированные эпизоды |
| **L3** | Long-Term | Neo4j | Месяцы-годы | Знания, паттерны, стратегии |

**Консолидация** — автоматическое перемещение важной информации вверх:
```
L0 → L1 → L2 → L3
     ↓     ↓     ↓
   (decay) (decay) (decay)
```

Неважная информация забывается (decay), важная поднимается выше.

### 2. Dual-Process Architecture

Две системы работают параллельно:

```
FAST SYSTEM (синхронно, во время запроса)
├── Получить сообщение пользователя
├── Найти релевантную память (retrieval)
├── Построить контекст
├── Сгенерировать ответ (LLM)
└── Вернуть ответ

SLOW SYSTEM (асинхронно, в фоне)
├── Извлечь сущности из диалога
├── Сохранить в граф
├── Консолидировать память (L0→L1→L2→L3)
├── Обучиться на результатах
└── Очистить старое (GC)
```

**Почему это важно:**
- Fast System не ждёт сохранения — ответ быстрый
- Slow System обрабатывает данные когда есть время
- Resilience: если Slow падает, Fast продолжает работать

### 3. FractalMemory — главный класс

**НЕ используй Graphiti напрямую.** Вся работа через FractalMemory:

```python
# ❌ НЕПРАВИЛЬНО
from graphiti_core import Graphiti
graphiti = Graphiti(...)
await graphiti.add_episode(...)

# ✅ ПРАВИЛЬНО
from src.core.memory import FractalMemory
memory = FractalMemory(config)
await memory.remember(content)
await memory.recall(query)
```

**Почему:**
1. FractalMemory добавляет фрактальную логику (уровни, консолидация)
2. FractalMemory добавляет soft delete
3. FractalMemory добавляет метрики
4. Если Graphiti изменится — меняем только адаптер

### 4. Soft Delete

**НИКОГДА не удаляй данные сразу.** Используй soft delete:

```python
# ❌ НЕПРАВИЛЬНО
await graph.execute_cypher("DETACH DELETE node")

# ✅ ПРАВИЛЬНО
await graph.execute_cypher("""
    MATCH (n {id: $id})
    SET n.deleted = true,
        n.deleted_at = datetime()
""")
```

**Почему:**
- Можно восстановить случайно удалённое
- Нет потери связей в графе
- Физическое удаление — через неделю, после проверки

---

## 🔧 Компоненты системы

### Обязательные компоненты (MVP)

| Компонент | Технология | Файл | Назначение |
|-----------|------------|------|------------|
| **FractalMemory** | Python | `src/core/memory.py` | Главный класс памяти |
| **GraphitiAdapter** | Python | `src/core/graphiti_adapter.py` | Обёртка над Graphiti |
| **Neo4j** | Docker | `docker-compose.yml` | Граф знаний |
| **Redis** | Docker | `docker-compose.yml` | Event bus, кэш |
| **Migrations** | Cypher | `migrations/` | Схема БД |

### Компоненты Phase 2+

| Компонент | Файл | Назначение |
|-----------|------|------------|
| **HybridRetriever** | `src/core/retrieval.py` | Умный поиск |
| **ReasoningBank** | `src/core/learning.py` | Самообучение |
| **CircuitBreaker** | `src/infrastructure/circuit_breaker.py` | Отказоустойчивость |
| **EventBus** | `src/infrastructure/event_bus.py` | Асинхронные события |

---

## 📐 Схема данных (Neo4j)

### Узлы (Nodes)

```cypher
// Сущность (персона, проект, концепт)
(:Entity {
    id: String,
    name: String,
    type: String,
    embedding: List<Float>,
    importance_score: Float,
    access_count: Int,
    created_at: DateTime,
    last_accessed: DateTime,
    // Soft delete
    deleted: Boolean,
    deleted_at: DateTime
})

// Эпизод (событие, разговор)
(:Episode {
    id: String,
    content: String,
    summary: String,
    timestamp: DateTime,
    source: String,
    importance_score: Float,
    outcome: String,  // success/failure/neutral
    level: Int,       // 1=MTM, 2=LTM
    // Soft delete
    deleted: Boolean,
    deleted_at: DateTime
})

// Стратегия (паттерн поведения)
(:Strategy {
    id: String,
    description: String,
    applicable_contexts: List<String>,
    success_count: Int,
    failure_count: Int,
    confidence: Float,
    // Soft delete
    deleted: Boolean,
    deleted_at: DateTime
})
```

### Связи (Relationships)

```cypher
(:Entity)-[:MENTIONED_IN]->(:Episode)
(:Entity)-[:RELATED_TO {strength: Float}]->(:Entity)
(:Episode)-[:LED_TO {outcome: String}]->(:Episode)
(:Strategy)-[:USED_IN]->(:Episode)
(:Strategy)-[:SUCCEEDED_AT]->(:Task)
(:Strategy)-[:FAILED_AT]->(:Task)
```

---

## 🔄 Жизненный цикл данных

```
1. СОЗДАНИЕ
   User message → FractalMemory.remember() → L0 (working memory)

2. КОНСОЛИДАЦИЯ (автоматически, в фоне)
   L0 → L1 (если важно)
   L1 → L2 (если часто используется)
   L2 → L3 (если паттерн)

3. RETRIEVAL
   Query → FractalMemory.recall() → Hybrid search → Results

4. DECAY (автоматически, в фоне)
   importance_score *= decay_rate
   Если importance < threshold → soft delete

5. GARBAGE COLLECTION (еженедельно)
   Soft deleted + age > 7 days → physical delete
```

---

## 🎯 Целевые метрики

| Метрика | Цель | Как измерять |
|---------|------|--------------|
| Token usage | -90% | `tokens_used / baseline_tokens` |
| Retrieval latency P95 | <500ms | OpenTelemetry spans |
| Task success rate | +30% | `successes / total_tasks` |
| Memory growth | Линейный | Neo4j node count |

---

## ⚠️ Важные ограничения

### Что система НЕ делает:
- ❌ Не заменяет LLM — только дополняет память
- ❌ Не работает без Neo4j — это обязательный компонент
- ❌ Не гарантирует 100% recall — это probabilistic система

### Что требует внимания:
- ⚠️ Neo4j индексы обязательны — без них медленно
- ⚠️ Redis persistence обязательна — иначе потеря событий
- ⚠️ Миграции обязательны — схема должна быть консистентна

---

## 📚 Следующий шаг

Перейди к: **[02_PHASE1_SETUP.md](02_PHASE1_SETUP.md)** — настройка инфраструктуры

---

## 🔗 Связанные документы

- [02_PHASE1_SETUP.md](02_PHASE1_SETUP.md) — Docker, Neo4j, Redis
- [03_PHASE2_MEMORY.md](03_PHASE2_MEMORY.md) — FractalMemory код
- [04_PHASE3_LEARNING.md](04_PHASE3_LEARNING.md) — ReasoningBank
- [05_PHASE4_PRODUCTION.md](05_PHASE4_PRODUCTION.md) — Мониторинг
