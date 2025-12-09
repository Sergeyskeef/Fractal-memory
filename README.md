# Marka AI — Fractal Memory Agent

Лёгкий лендинг для репозитория. Подробная архитектура и история расследований вынесены в `docs/` (оригинал) и во временные консолидированные заметки в `notes/`.

## Что это
- AI-агент с иерархической памятью L0–L3 (Redis + Neo4j/Graphiti).
- Батч-консолидация (15 сообщений) с LLM-саммари (gpt-5-mini) и JSON-контрактом.
- Reasoning Bank (Neo4j) для стратегий/опыта, эвристический Judge по фидбеку пользователя.
- FastAPI backend + React frontend; Docker Compose для локального запуска.

## Быстрый старт
```bash
cp .env.example .env        # заполни NEO4J_PASSWORD, OPENAI_API_KEY
docker compose up -d --build
python migrations/run_migrations.py
python scripts/run_smoke_test.py --reset   # один прогон с форензик-отчётом
```

## Полезные документы
- Основная документация (не изменяем): `docs/01_ARCHITECTURE.md` → … → `docs/05_PHASE4_PRODUCTION.md`.
- Временные конспекты (для собеседования):  
  - `notes/ARCHITECTURE.md` — сжатый обзор слоёв, консолидации, хранилищ.  
  - `notes/DEV_JOURNEY.md` — ключевые инциденты (гонка L0→L1, саммари, L3=5), процедуры тестов, решения по качеству.

### Для рекрутеров/ревьюеров: «как всё начиналось»
- Базовая домашняя документация по фазам (детально и аккуратно написана в начале проекта):  
  - `docs/01_ARCHITECTURE.md` — стартовая архитектура и мотивация  
  - `docs/02_PHASE1_SETUP.md` — инфраструктура и базовый сетап  
  - `docs/03_PHASE2_MEMORY.md` — реализация памяти L0–L3  
  - `docs/04_PHASE3_LEARNING.md` — самообучение и Reasoning Bank  
  - `docs/05_PHASE4_PRODUCTION.md` — стабилизация, мониторинг, прод-практики  
Эти документы — хороший показатель инженерной дисциплины с первых шагов.

## Стек
- Python 3.11, AsyncIO
- Redis Streams (L0/L1, locks), Neo4j/Graphiti (L2/L3)
- FastAPI, React/TS
- Docker Compose

## Основные команды
- `docker compose up -d` — поднять стек
- `python migrations/run_migrations.py` — миграции Neo4j
- `python scripts/run_smoke_test.py --reset` — смок + инспекция (L1/L2/L3)
- `pytest` или `make test` — тесты

## Навигация по коду
- `src/core/memory.py` — FractalMemory (L0–L3, консолидация)
- `src/core/redis_store.py`, `src/core/graphiti_store.py` — адаптеры Redis/Graphiti
- `src/core/reasoning.py` — Reasoning Bank
- `backend/main.py`, `backend/routers/` — API
- `scripts/` — smoke/reset/inspect утилиты
- `tests/` — unit + integration (`test_memory_v2_pipeline.py`)

## Предупреждения
- Всегда создавай индексы Neo4j перед записью.
- Не обходи FractalMemory: не пиши напрямую в Graphiti.
- Используй soft delete; не пропускай миграции.

## Статус
- Проект в активной фазе разработки: стабилизация консолидации, улучшение саммари и диагностики. Обратная связь и PR приветствуются.

## Лицензия
- MIT License © 2025 Sergey Skripinskiy (`LICENSE` в корне).

## Если нужно глубже
- Читай `docs/` по порядку (01 → 05) — оригинальные материалы.
- См. `notes/DEV_JOURNEY.md` для краткой истории багфиксов и текущих рисков.
