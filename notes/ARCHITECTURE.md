# ARCHITECTURE OVERVIEW (Fractal Memory Agent)

> Временный консолидированный обзор (оригинальные документы не трогаем).  
> Источники: `docs/01_ARCHITECTURE.md`, `COMPLETE_ARCHITECTURE_ANALYSIS_RU.md`, `SCHEMA_ANALYSIS_RU.md`, `REFACTORING_PLAN.md`, отчёты фаз.

## Слои памяти (L0–L3)
- **L0 (Working, Redis Streams):** сырые сообщения, короткое время жизни; триггер консолидации по батчу (15).  
- **L1 (Short-Term, Redis Hash/List):** саммари батчей; хранит `session_id`, `summary`, `importance`, ссылки на L0.  
- **L2 (Episodic, Neo4j/Graphiti):** эпизоды с `scale=meso`, связи к пользователю, темам; задаёт долговременный контекст.  
- **L3 (Entities/Knowledge, Graphiti):** извлечённые сущности (Entity), Fact/Skill — при наличии; используется в поиске и связях.

## Поток консолидации
- **L0 → L1:** батч 15 сообщений; LLM-саммари (gpt-5-mini) в JSON; запись в L1 Hash + summary list; источник `type=conversation_summary`; пометка в Redis set; очистка буфера L0.  
- **L1 → L2:** пропускает `conversation_summary` (уже в L2); переносит важные/часто используемые; устанавливает `scale=meso`.  
- **Locks:** SETNX в Redis `memory:{user}:consolidation_lock` (TTL 60s) + python-lock для сериализации.

## Хранилища и адаптеры
- **RedisMemoryStore:** XADD + MAXLEN, SCAN для L1, LPUSH list для быстрых саммари.  
- **GraphitiStore (Neo4j):** `add_episode(content, metadata.scale)`, возможность дополнительного Cypher для `scale`; поиск `graphiti.search`.  
- **Reasoning Bank:** узлы Strategy/Experience, связи EVOLVED_FROM/APPLIED_IN, outcome-статистика (weighted average).

## Агент и контекст
- **FractalAgent:** каскад контекста L0 (15 raw) → L1 (3 summaries) → L2 search (сниженный лимит при наличии L0/L1).  
- **Judge:** эвристика SUCCESS/FAIL/PARTIAL/UNKNOWN по следующему сообщению пользователя.  
- **Prompt X-Ray:** диагностический вывод перед вызовом LLM.

## Инфраструктура
- **API:** FastAPI `/chat`, `/memory` статы.  
- **Тесты:** `tests/integration/test_memory_v2_pipeline.py` — 15→1 батч, lock, контекст-каскад.  
- **Скрипты:** `scripts/run_smoke_test.py` (см. DEV_JOURNEY), `scripts/reset_memory.py`, `scripts/inspect_everything.py`.

## Ключевые решения
- L0→L1 только через батч + саммари (нет прямых L0→L2).  
- Масштаб эпизодов ставится вручную (`scale=meso`).  
- Redis/Neo4j обязательны; консистентность через lock + пометки `consolidated_set`.  
- LLM внутренняя — `gpt-5-mini` (раньше nano).  
- Консолидация «мягкая»: без hard delete, с декорацией importance/decay.

