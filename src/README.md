# Source Code

## 📂 Структура

```
src/
├── core/                           ← Ядро системы памяти
│   ├── memory.py                   ← FractalMemory (реализовано)
│   ├── graphiti_adapter.py         ← Адаптер для Graphiti (реализовано)
│   ├── learning.py                 ← ReasoningBank (реализовано)
│   └── retrieval.py                ← HybridRetriever (реализовано)
│
├── infrastructure/                 ← Инфраструктурные компоненты
│   ├── circuit_breaker.py          ← Circuit Breaker (реализовано)
│   ├── health.py                   ← Health checks (реализовано)
│   ├── metrics.py                  ← Prometheus метрики (реализовано)
│   ├── rate_limiter.py             ← Rate limiting & quotas (реализовано)
│   ├── retry.py                    ← Retry c экспоненциальной задержкой (реализовано)
│   └── event_bus.py / observability.py ← ⏳ Планируется (см. docs/05_PHASE4_PRODUCTION.md)
│
└── agent.py                        ← FractalAgent (реализовано)
```

---

## 📚 Где взять код для реализации

Полный код каждого файла находится в соответствующем документе:

| Файл | Документ | Раздел | Статус |
|------|----------|--------|--------|
| Файл | Документ | Раздел | Статус |
|------|----------|--------|--------|
| `memory.py` | `docs/03_PHASE2_MEMORY.md` | "2️⃣ FractalMemory" | ✅ Реализовано |
| `graphiti_adapter.py` | `docs/03_PHASE2_MEMORY.md` | "1️⃣ GraphitiAdapter" | ✅ Реализовано |
| `learning.py` | `docs/04_PHASE3_LEARNING.md` | "1️⃣ ReasoningBank" | ✅ Реализовано |
| `rate_limiter.py` | `docs/05_PHASE4_PRODUCTION.md` | "4️⃣ Production Hardening" | ✅ Реализовано |
| `retry.py` | `docs/05_PHASE4_PRODUCTION.md` | "4️⃣ Production Hardening" | ✅ Реализовано |
| `retrieval.py` | `docs/03_PHASE2_MEMORY.md` | "3️⃣ HybridRetriever" | ✅ Реализовано |
| `event_bus.py` | `docs/05_PHASE4_PRODUCTION.md` | "2️⃣ Event Bus" | ⏳ В планах (Phase 4) |
| `observability.py` | `docs/05_PHASE4_PRODUCTION.md` | "3️⃣ Observability" | ⏳ В планах (Phase 4) |
| `agent.py` | `docs/04_PHASE3_LEARNING.md` | "2️⃣ Agent Orchestration" | ✅ Реализовано |

---

## 🚀 Быстрый старт

### 1. Установить зависимости

```bash
# С Poetry (рекомендуется)
poetry install --with dev

# Или с pip
pip install -r requirements.txt
```

### 2. Реализовать код

**Phase 2** (обязательно):
1. Открой `docs/03_PHASE2_MEMORY.md`
2. Скопируй код `GraphitiAdapter` → `src/core/graphiti_adapter.py`
3. Скопируй код `FractalMemory` → `src/core/memory.py`
4. Запусти тесты: `make test-unit`

**Phase 3** (обязательно):
1. Открой `docs/04_PHASE3_LEARNING.md`
2. Скопируй код `ReasoningBank` → `src/core/learning.py`
3. Запусти тесты: `make test`

**Phase 4** (production):
1. Открой `docs/05_PHASE4_PRODUCTION.md`
2. Реализуй `circuit_breaker.py`, `event_bus.py`
3. Настрой мониторинг

### 3. Запустить тесты

```bash
# Все тесты
make test

# Только unit тесты (без Neo4j)
make test-unit

# Только integration (требуется Neo4j)
make test-integration
```

### 4. Попробовать примеры

```bash
# После реализации FractalMemory
python examples/01_basic_usage.py

# После реализации ReasoningBank
python examples/02_learning_demo.py
```

---

## 💡 Примеры использования

### Базовое использование (после реализации)

```python
import asyncio
from src.core.memory import FractalMemory

async def main():
    # Конфигурация
    config = {
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "your_password",
        "l0_capacity": 10,
        "l1_capacity": 50,
    }

    # Инициализация
    memory = FractalMemory(config)
    await memory.initialize()

    # Сохранение
    await memory.remember("User prefers Python")

    # Извлечение
    results = await memory.recall("programming language preference")

    # Консолидация
    await memory.consolidate()

    # Cleanup
    await memory.close()

asyncio.run(main())
```

### С Pydantic валидацией

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MemoryConfig(BaseModel):
    """Конфигурация памяти с автовалидацией"""
    neo4j_uri: str = Field(..., description="Neo4j connection URI")
    neo4j_user: str = "neo4j"
    neo4j_password: str = Field(..., min_length=8)

    l0_capacity: int = Field(default=10, ge=1, le=100)
    l1_capacity: int = Field(default=50, ge=10, le=1000)
    importance_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    class Config:
        validate_assignment = True  # Валидация при изменении

# Использование
config = MemoryConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_password="securepassword123"
)

memory = FractalMemory(config.model_dump())
```

---

## 🔧 Разработка

### Линтинг и форматирование

```bash
# Проверить код
make lint

# Форматировать код
make format

# Проверить типы
mypy src/
```

### Перед коммитом

```bash
# Запустить все проверки
make pre-commit

# Или через CI
make ci
```

---

## 📝 Соглашения о коде

### Именование

- **Классы**: `PascalCase` (`FractalMemory`, `GraphitiAdapter`)
- **Функции/методы**: `snake_case` (`remember()`, `get_stats()`)
- **Константы**: `UPPER_SNAKE_CASE` (`L0_CAPACITY`)
- **Приватные**: `_leading_underscore` (`_consolidate_internal()`)

### Докстринги

```python
async def remember(self, content: str, importance_score: float = 1.0) -> str:
    """
    Сохранить информацию в память.

    Args:
        content: Текст для сохранения
        importance_score: Важность (0.0-1.0)

    Returns:
        ID сохраненного эпизода

    Raises:
        ValueError: Если importance_score вне диапазона
    """
```

### Type hints

Используй type hints везде:

```python
from typing import List, Dict, Optional

async def recall(
    self,
    query: str,
    levels: Optional[List[int]] = None
) -> List[SearchResult]:
    """..."""
```

---

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'src'

```bash
# Убедись что запускаешь из корня проекта
cd /path/to/fractal_memory_updated

# Или добавь в PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Тесты не находят src/

```bash
# conftest.py уже настроен, но если проблемы:
pytest tests/ -v --tb=short
```

---

## 📚 Дальнейшие шаги

1. **После Phase 2** → Запусти `examples/01_basic_usage.py`
2. **После Phase 3** → Запусти `examples/02_learning_demo.py`
3. **Перед деплоем** → Прочитай `docs/05_PHASE4_PRODUCTION.md`

Удачи! 🚀
