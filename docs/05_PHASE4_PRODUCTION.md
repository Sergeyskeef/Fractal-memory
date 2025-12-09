# 05. Phase 4: Production & Мониторинг

## 🎯 Цель

Подготовить систему к production: мониторинг, отказоустойчивость, GC.

**Время**: 1-2 недели  
**Результат**: Production-ready система с полным observability

---

## 📋 Чек-лист Phase 4

- [x] Circuit Breakers добавлены
- [ ] OpenTelemetry настроен (опционально)
- [x] Prometheus метрики экспортируются
- [ ] Grafana dashboards созданы (опционально)
- [x] Memory GC работает
- [x] Health checks работают
- [ ] Load testing пройден (опционально)
- [x] **FastAPI Backend реализован** (`backend/main.py`, `backend/routers/`)
- [x] **React Frontend интегрирован** (`fractal-memory-interface/`)
- [x] **Docker Compose настроен** для полного стека (neo4j, redis, backend, frontend)
- [x] **CORS настроен** для работы фронтенда с бэкендом

---

## 1️⃣ Circuit Breaker

### Файл `src/infrastructure/circuit_breaker.py`:

```python
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
```

---

## 2️⃣ Prometheus Метрики

### Файл `src/infrastructure/metrics.py`:

```python
"""
Prometheus метрики для мониторинга.
"""

from prometheus_client import Counter, Histogram, Gauge

# Токены
tokens_used = Counter(
    "agent_tokens_used_total",
    "Total tokens used",
    ["component"]
)

tokens_per_query = Histogram(
    "agent_tokens_per_query",
    "Tokens per query",
    buckets=[100, 500, 1000, 2000, 5000, 10000]  # Обновлено: max_tokens увеличен до 5000
)

# Память
memory_size = Gauge(
    "agent_memory_size",
    "Memory size by level",
    ["level"]
)

# Латентность
retrieval_latency = Histogram(
    "retrieval_latency_seconds",
    "Retrieval latency",
    ["stage"],
    buckets=[0.01, 0.05, 0.1, 0.3, 0.5, 1.0]
)

# Circuit Breaker
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"]
)

# Learning
strategy_success_rate = Gauge(
    "strategy_success_rate",
    "Strategy success rate",
    ["strategy_id"]
)
```

---

## 3️⃣ Memory Garbage Collection с Soft Delete

### Обновление в `src/core/memory.py`:

```python
async def garbage_collect(
    self, 
    soft_delete_age_days: int = 7,
    importance_threshold: float = 0.2
) -> Dict:
    """
    Garbage Collection:
    1. Soft delete низко-важных записей
    2. Hard delete записей с soft delete старше N дней
    
    ⚠️ ВАЖНО: Hard delete только после soft delete периода!
    """
    self._ensure_initialized()
    
    stats = {
        "soft_deleted": 0,
        "hard_deleted": 0,
        "errors": []
    }
    
    # 1. Soft delete низко-важных
    try:
        soft_result = await self.graph.execute_cypher(
            """
            MATCH (n)
            WHERE n.deleted = false
              AND n.importance_score < $threshold
              AND n.access_count = 0
              AND n.timestamp < datetime() - duration({days: 30})
            SET n.deleted = true,
                n.deleted_at = datetime()
            RETURN count(n) as count
            """,
            {"threshold": importance_threshold}
        )
        stats["soft_deleted"] = soft_result[0]["count"] if soft_result else 0
        
    except Exception as e:
        stats["errors"].append(f"Soft delete error: {e}")
        logger.error(f"GC soft delete failed: {e}")
    
    # 2. Hard delete (только после soft delete периода!)
    try:
        hard_result = await self.graph.execute_cypher(
            """
            MATCH (n)
            WHERE n.deleted = true
              AND n.deleted_at < datetime() - duration({days: $days})
            WITH n LIMIT 1000
            DETACH DELETE n
            RETURN count(n) as count
            """,
            {"days": soft_delete_age_days}
        )
        stats["hard_deleted"] = hard_result[0]["count"] if hard_result else 0
        
    except Exception as e:
        stats["errors"].append(f"Hard delete error: {e}")
        logger.error(f"GC hard delete failed: {e}")
    
    logger.info(f"GC complete: {stats}")
    return stats
```

---

## 4️⃣ Health Checks

### Файл `src/infrastructure/health.py`:

```python
"""
Health checks для всех компонентов.
"""

from typing import Dict
import asyncio


async def check_neo4j(graph) -> Dict:
    """Проверка Neo4j"""
    try:
        result = await graph.execute_cypher("RETURN 1 as n", {})
        return {
            "status": "healthy",
            "latency_ms": 0  # TODO: измерить
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_redis(redis_client) -> Dict:
    """Проверка Redis"""
    try:
        await redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def full_health_check(components: Dict) -> Dict:
    """Полная проверка всех компонентов"""
    results = {}
    
    if "graph" in components:
        results["neo4j"] = await check_neo4j(components["graph"])
    
    if "redis" in components:
        results["redis"] = await check_redis(components["redis"])
    
    # Общий статус
    all_healthy = all(
        r.get("status") == "healthy" 
        for r in results.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": results
    }
```

---

## 5️⃣ Docker Compose для Production

### Добавить в `docker-compose.yml`:

```yaml
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - fractal-memory-network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - fractal-memory-network

volumes:
  grafana_data:
```

### Файл `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fractal-memory'
    static_configs:
      - targets: ['host.docker.internal:8000']
  
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']
```

---

## 6️⃣ React Frontend

### Архитектура

Frontend реализован как React приложение с TypeScript в папке `fractal-memory-interface/`:

```
fractal-memory-interface/
├── App.tsx                    # Главный компонент
├── components/
│   ├── Chat/                  # Компоненты чата (InputArea, MessageBubble)
│   ├── Memory/               # Компоненты памяти (StatsPanel, MemoryBrowser, GraphView)
│   └── Layout/                # Компоненты макета (Header)
├── services/
│   └── api.ts                 # API клиент для взаимодействия с FastAPI
├── types.ts                   # TypeScript типы
├── constants.ts                # Константы (API_URL)
└── Dockerfile                 # Multi-stage Docker build
```

### API Эндпоинты

Frontend взаимодействует с бэкендом через следующие эндпоинты:

1. **`POST /chat`** — отправка сообщения агенту
   - Request: `{ message: string }`
   - Response: `{ response: string, context_count: number, strategies_used: string[], processing_time_ms: number }`

2. **`GET /memory/stats`** — статистика памяти
   - Response: `{ l0_count: number, l1_count: number, l2_count: number, l3_count: number, last_consolidation?: string }`

3. **`GET /memory/{level}`** — получение узлов памяти
   - `level`: `'all' | 'l0' | 'l1' | 'l2' | 'l3'`
   - Response: `MemoryNode[]` (массив узлов с полями: id, label, content, level, importance, created_at, connections)

4. **`POST /memory/consolidate`** — принудительная консолидация
   - Response: `{ status: string, l0_to_l1?: number, l1_to_l2?: number }`

5. **`POST /memory/remember`** — сохранение информации в память
   - Request: `{ content: string, importance?: number }`
   - Response: `{ status: string, id: string }`

### Docker Интеграция

Frontend добавлен в `docker-compose.yml` как отдельный сервис:

```yaml
frontend:
  build:
    context: ./fractal-memory-interface
    dockerfile: Dockerfile
  ports:
    - "3000:80"
  depends_on:
    backend:
      condition: service_healthy
  restart: unless-stopped
  networks:
    - fractal-memory-network
```

### CORS Настройка

В `backend/main.py` добавлен CORSMiddleware:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production заменить на конкретные домены
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Запуск

После запуска `docker compose up -d --build`:
- Frontend доступен на http://localhost:3000
- Backend API доступен на http://localhost:8000
- API документация: http://localhost:8000/docs

### Особенности

- **Типобезопасность**: TypeScript типы синхронизированы с FastAPI моделями
- **Обработка ошибок**: Улучшенная обработка ошибок API с детальными сообщениями
- **Визуализация**: Граф узлов памяти с помощью D3.js (в GraphView компоненте)
- **Реальное время**: Автоматическое обновление статистики после каждого диалога

---

## ✅ Критерии завершения Phase 4

- [x] Circuit Breakers защищают от каскадных отказов
- [x] Prometheus метрики экспортируются
- [ ] Grafana показывает dashboards (опционально)
- [x] GC с soft delete работает
- [x] Health checks проходят
- [ ] Система выдерживает нагрузку (load test) (опционально)
- [x] **FastAPI Backend работает** (все эндпоинты протестированы)
- [x] **React Frontend интегрирован** (доступен на порту 3000)
- [x] **CORS настроен** для работы фронтенда с бэкендом
- [x] **Регрессионное тестирование пройдено** (53 unit + E2E тесты)

---

## 📚 Следующий шаг

Перейди к: **[06_FUTURE_ROADMAP.md](06_FUTURE_ROADMAP.md)** — что делать после MVP
