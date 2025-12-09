# Migration Guide

## Как работают миграции

Миграции — это способ управлять схемой Neo4j. Каждая миграция:
1. Имеет версию (001, 002, ...)
2. Выполняется один раз
3. Записывается в узел `Migration`

## Структура файлов

```
migrations/
├── MIGRATION_GUIDE.md      ← Ты здесь
├── 001_initial_schema.cypher
├── 002_add_soft_delete.cypher
└── run_migrations.py
```

## Как добавить новую миграцию

1. Создай файл `003_название.cypher`
2. В конце добавь:
```cypher
MERGE (m:Migration {version: 3})
SET m.applied_at = datetime(),
    m.name = 'название';
```
3. Запусти: `python migrations/run_migrations.py`

## Запуск миграций

```bash
# Убедись что .env настроен
python migrations/run_migrations.py
```

## Откат миграции

⚠️ Neo4j не поддерживает автоматический откат!

Для отката:
1. Создай новую миграцию которая отменяет изменения
2. Или восстанови из backup

## Проверка статуса

```cypher
// В Neo4j Browser
MATCH (m:Migration)
RETURN m.version, m.name, m.applied_at
ORDER BY m.version;
```
