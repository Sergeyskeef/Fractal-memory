# 02. Phase 1: Настройка инфраструктуры

## 🎯 Цель

Запустить Neo4j + Redis + создать индексы + запустить миграции.

**Время**: 30-60 минут  
**Результат**: Работающая инфраструктура, готовая к разработке

---

## 📋 Чек-лист Phase 1

- [ ] Docker и Docker Compose установлены
- [ ] docker-compose.yml создан
- [ ] .env файл настроен
- [ ] Контейнеры запущены и healthy
- [ ] Neo4j индексы созданы
- [ ] Миграции выполнены
- [ ] Smoke test пройден

---

## 1️⃣ Docker Compose

### Создай файл `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # ═══════════════════════════════════════════════════════
  # NEO4J - Граф знаний
  # ═══════════════════════════════════════════════════════
  neo4j:
    image: neo4j:5.15.0
    container_name: fractal-memory-neo4j
    ports:
      - "7474:7474"  # HTTP (Browser UI)
      - "7687:7687"  # Bolt protocol
    environment:
      # Аутентификация
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      
      # ⚠️ КРИТИЧНО: Память
      # Дефолт 512MB → OutOfMemory через неделю!
      - NEO4J_server_memory_heap_initial__size=2G
      - NEO4J_server_memory_heap_max__size=4G
      - NEO4J_server_memory_pagecache_size=2G
      
      # Производительность
      - NEO4J_db_query_parallel_enabled=true
      - NEO4J_server_bolt_thread__pool__min__size=5
      - NEO4J_server_bolt_thread__pool__max__size=400
      - NEO4J_db_transaction_timeout=30s
      
      # Метрики
      - NEO4J_server_metrics_enabled=true
      - NEO4J_server_metrics_prometheus_enabled=true
      - NEO4J_server_metrics_prometheus_endpoint=0.0.0.0:2004
      
      # APOC (для advanced операций)
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
    
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ${NEO4J_PASSWORD} 'RETURN 1'"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    
    networks:
      - fractal-memory-network
    
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  # ═══════════════════════════════════════════════════════
  # REDIS - Event Bus и кэш
  # ═══════════════════════════════════════════════════════
  redis:
    image: redis:7.2-alpine
    container_name: fractal-memory-redis
    ports:
      - "6379:6379"
    command: >
      redis-server
      --appendonly yes
      --maxmemory 1gb
      --maxmemory-policy allkeys-lru
    
    volumes:
      - redis_data:/data
    
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    
    networks:
      - fractal-memory-network

volumes:
  neo4j_data:
  neo4j_logs:
  redis_data:

networks:
  fractal-memory-network:
    driver: bridge
```

### Создай файл `.env`:

```bash
# .env
# ⚠️ НЕ КОММИТЬ В GIT! Добавь в .gitignore

# Neo4j
NEO4J_PASSWORD=your_secure_password_change_me
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j

# Redis
REDIS_URL=redis://localhost:6379

# LLM (OpenAI)
OPENAI_API_KEY=sk-your-key-here

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

### Создай `.env.example` (для команды):

```bash
# .env.example
# Скопируй в .env и заполни значения

NEO4J_PASSWORD=change_me
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

---

## 2️⃣ Запуск контейнеров

```bash
# Запуск
docker-compose up -d

# Проверка статуса
docker-compose ps

# Ожидаемый вывод:
# NAME                    STATUS              PORTS
# fractal-memory-neo4j    healthy             0.0.0.0:7474->7474, 0.0.0.0:7687->7687
# fractal-memory-redis    healthy             0.0.0.0:6379->6379

# Если не healthy — подожди 30 секунд и проверь снова
```

### Проверка Neo4j:
```bash
# Открой в браузере: http://localhost:7474
# Login: neo4j / <твой пароль из .env>
# Выполни: RETURN 1
# Должен вернуть: 1
```

### Проверка Redis:
```bash
docker exec -it fractal-memory-redis redis-cli ping
# Ожидаемый ответ: PONG
```

---

## 3️⃣ Создание индексов Neo4j

### Файл `scripts/create_indexes.cypher`:

```cypher
// ═══════════════════════════════════════════════════════════
// ⚠️ КРИТИЧНО: Создать ДО добавления данных!
// Без индексов система деградирует через 2-4 недели
// ═══════════════════════════════════════════════════════════

// 1. Entity name (самый частый запрос)
CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

// 2. Episode timestamp (temporal queries)
CREATE INDEX episode_timestamp_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.timestamp);

// 3. Vector index для semantic search
// ⚠️ Измени dimensions если используешь другую модель!
CREATE VECTOR INDEX entity_embedding_idx IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};

// 4. Composite: importance + time
CREATE INDEX entity_importance_time_idx IF NOT EXISTS
FOR (e:Entity) ON (e.importance_score, e.last_accessed);

// 5. Strategy success rate
CREATE INDEX strategy_success_idx IF NOT EXISTS
FOR (s:Strategy) ON (s.success_rate);

// 6. Soft delete index (для GC)
CREATE INDEX entity_deleted_idx IF NOT EXISTS
FOR (e:Entity) ON (e.deleted, e.deleted_at);

CREATE INDEX episode_deleted_idx IF NOT EXISTS
FOR (ep:Episode) ON (ep.deleted, ep.deleted_at);

// 7. Memory level
CREATE INDEX memory_level_idx IF NOT EXISTS
FOR (m:Memory) ON (m.level);

// Проверка
SHOW INDEXES;
```

### Выполнение:

```bash
# Способ 1: Через docker exec
docker exec -i fractal-memory-neo4j cypher-shell \
  -u neo4j \
  -p YOUR_PASSWORD \
  < scripts/create_indexes.cypher

# Способ 2: Интерактивно
docker exec -it fractal-memory-neo4j cypher-shell -u neo4j -p YOUR_PASSWORD
# Затем скопировать команды из файла

# Проверить что индексы созданы:
# SHOW INDEXES;
# Все должны быть в состоянии ONLINE
```

---

## 4️⃣ Миграции

### Файл `migrations/001_initial_schema.cypher`:

```cypher
// Migration 001: Initial Schema
// Версия: 1
// Дата: 2025-01-25

// Создать constraint на уникальность ID
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
FOR (ep:Episode) REQUIRE ep.id IS UNIQUE;

CREATE CONSTRAINT strategy_id_unique IF NOT EXISTS
FOR (s:Strategy) REQUIRE s.id IS UNIQUE;

// Записать версию миграции
MERGE (m:Migration {version: 1})
SET m.applied_at = datetime(),
    m.name = 'initial_schema';
```

### Файл `migrations/002_add_soft_delete.cypher`:

```cypher
// Migration 002: Add Soft Delete Fields
// Версия: 2
// Дата: 2025-01-25

// Добавить поля soft delete ко всем существующим узлам
MATCH (e:Entity)
WHERE e.deleted IS NULL
SET e.deleted = false;

MATCH (ep:Episode)
WHERE ep.deleted IS NULL
SET ep.deleted = false;

MATCH (s:Strategy)
WHERE s.deleted IS NULL
SET s.deleted = false;

// Записать версию миграции
MERGE (m:Migration {version: 2})
SET m.applied_at = datetime(),
    m.name = 'add_soft_delete';
```

### Файл `migrations/run_migrations.py`:

```python
#!/usr/bin/env python3
"""
Скрипт запуска миграций Neo4j

Использование:
    python migrations/run_migrations.py

Миграции выполняются по порядку, пропускаются уже выполненные.
"""

import os
import glob
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_applied_migrations(driver) -> set:
    """Получить список уже выполненных миграций"""
    with driver.session() as session:
        result = session.run("MATCH (m:Migration) RETURN m.version as version")
        return {record["version"] for record in result}

def apply_migration(driver, filepath: str, version: int):
    """Применить одну миграцию"""
    print(f"Applying migration {version}: {filepath}")
    
    with open(filepath, 'r') as f:
        cypher = f.read()
    
    with driver.session() as session:
        # Разбить на отдельные команды (по ;)
        commands = [cmd.strip() for cmd in cypher.split(';') if cmd.strip()]
        
        for cmd in commands:
            if cmd and not cmd.startswith('//'):
                session.run(cmd)
    
    print(f"  ✅ Migration {version} applied")

def main():
    if not NEO4J_PASSWORD:
        print("❌ NEO4J_PASSWORD not set in .env")
        return
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Проверить подключение
        with driver.session() as session:
            session.run("RETURN 1")
        print("✅ Connected to Neo4j")
        
        # Получить выполненные миграции
        applied = get_applied_migrations(driver)
        print(f"Already applied: {applied}")
        
        # Найти все файлы миграций
        migration_files = sorted(glob.glob("migrations/*.cypher"))
        
        for filepath in migration_files:
            # Извлечь версию из имени файла (001_xxx.cypher → 1)
            filename = os.path.basename(filepath)
            version = int(filename.split('_')[0])
            
            if version not in applied:
                apply_migration(driver, filepath, version)
            else:
                print(f"⏭️  Migration {version} already applied, skipping")
        
        print("\n✅ All migrations complete!")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()
```

### Запуск миграций:

```bash
# Установить зависимости
pip install neo4j python-dotenv

# Запустить миграции
python migrations/run_migrations.py

# Ожидаемый вывод:
# ✅ Connected to Neo4j
# Already applied: set()
# Applying migration 1: migrations/001_initial_schema.cypher
#   ✅ Migration 1 applied
# Applying migration 2: migrations/002_add_soft_delete.cypher
#   ✅ Migration 2 applied
# ✅ All migrations complete!
```

---

## 5️⃣ Smoke Test

### Файл `scripts/smoke_test.py`:

```python
#!/usr/bin/env python3
"""
Smoke test: проверка что всё работает

Использование:
    python scripts/smoke_test.py
"""

import os
import asyncio
from dotenv import load_dotenv
from neo4j import GraphDatabase
import redis

load_dotenv()

def check_neo4j():
    """Проверить Neo4j"""
    print("Checking Neo4j...")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # Проверить подключение
            result = session.run("RETURN 1 as n").single()
            assert result["n"] == 1, "Query failed"
            print("  ✅ Connection OK")
            
            # Проверить индексы
            indexes = session.run("SHOW INDEXES YIELD name, state").data()
            online_count = sum(1 for i in indexes if i["state"] == "ONLINE")
            print(f"  ✅ Indexes: {online_count} ONLINE")
            
            # Проверить миграции
            migrations = session.run(
                "MATCH (m:Migration) RETURN count(m) as count"
            ).single()["count"]
            print(f"  ✅ Migrations applied: {migrations}")
            
    finally:
        driver.close()
    
    return True

def check_redis():
    """Проверить Redis"""
    print("Checking Redis...")
    
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = redis.from_url(url)
    
    # Проверить подключение
    assert r.ping(), "Redis ping failed"
    print("  ✅ Connection OK")
    
    # Проверить запись/чтение
    r.set("smoke_test", "ok")
    value = r.get("smoke_test")
    assert value == b"ok", "Read/write failed"
    r.delete("smoke_test")
    print("  ✅ Read/Write OK")
    
    # Проверить persistence
    info = r.info("persistence")
    aof_enabled = info.get("aof_enabled", 0)
    print(f"  ✅ AOF persistence: {'enabled' if aof_enabled else 'disabled'}")
    
    return True

def main():
    print("=" * 50)
    print("SMOKE TEST: Fractal Memory Infrastructure")
    print("=" * 50)
    print()
    
    results = []
    
    try:
        results.append(("Neo4j", check_neo4j()))
    except Exception as e:
        print(f"  ❌ Neo4j FAILED: {e}")
        results.append(("Neo4j", False))
    
    print()
    
    try:
        results.append(("Redis", check_redis()))
    except Exception as e:
        print(f"  ❌ Redis FAILED: {e}")
        results.append(("Redis", False))
    
    print()
    print("=" * 50)
    print("RESULTS:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! Infrastructure is ready.")
        return 0
    else:
        print("⚠️  Some checks failed. Fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main())
```

### Запуск:

```bash
pip install redis

python scripts/smoke_test.py

# Ожидаемый вывод:
# ==================================================
# SMOKE TEST: Fractal Memory Infrastructure
# ==================================================
#
# Checking Neo4j...
#   ✅ Connection OK
#   ✅ Indexes: 7 ONLINE
#   ✅ Migrations applied: 2
#
# Checking Redis...
#   ✅ Connection OK
#   ✅ Read/Write OK
#   ✅ AOF persistence: enabled
#
# ==================================================
# RESULTS:
# ==================================================
#   Neo4j: ✅ PASS
#   Redis: ✅ PASS
#
# 🎉 All checks passed! Infrastructure is ready.
```

---

## 🔧 Troubleshooting

### Neo4j не запускается

```bash
# Проверить логи
docker logs fractal-memory-neo4j

# Частые проблемы:
# 1. Мало памяти → уменьши heap в docker-compose.yml
# 2. Порт занят → измени порты
# 3. Неверный пароль → проверь .env
```

### Redis не сохраняет данные

```bash
# Проверить что AOF включен
docker exec fractal-memory-redis redis-cli CONFIG GET appendonly
# Должно быть: appendonly yes

# Если нет — перезапусти с правильной командой
```

### Индексы не создаются

```bash
# Проверить статус индексов
docker exec -it fractal-memory-neo4j cypher-shell \
  -u neo4j -p YOUR_PASSWORD \
  "SHOW INDEXES YIELD name, state, populationPercent"

# Если state = POPULATING → подожди
# Если state = FAILED → удали и создай заново:
# DROP INDEX entity_name_idx;
# CREATE INDEX ...
```

### Vector index не работает

```bash
# Проверить версию Neo4j (нужна 5.11+)
docker exec fractal-memory-neo4j neo4j --version

# Проверить что dimensions правильные
# Если используешь другую модель → измени в create_indexes.cypher
```

---

## ✅ Критерии завершения Phase 1

- [ ] `docker-compose ps` показывает оба контейнера healthy
- [ ] `SHOW INDEXES` показывает все индексы ONLINE
- [ ] `python scripts/smoke_test.py` выводит "All checks passed"
- [ ] Миграции выполнены (есть узлы Migration в Neo4j)

---

## 📚 Следующий шаг

Перейди к: **[03_PHASE2_MEMORY.md](03_PHASE2_MEMORY.md)** — реализация FractalMemory
