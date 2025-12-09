# DEV JOURNEY & INCIDENT LOG

> Временная сводка расследований и багфиксов. Оригиналы отчётов остаются в корне/`audit_reports/`.

## Ключевые инциденты
- **Race L0→L1 (двойные эпизоды):** гонка между 15‑м и 16‑м сообщением; исправлено добавлением Redis SETNX lock (`memory:{user}:consolidation_lock`, TTL 60s) + python-lock. Для расследований добавлены: `scripts/run_smoke_test.py` (пауза 5s), `scripts/inspect_everything.py` (таймштампы L1/L2).
- **LLM саммари копипастило логи:** Nano игнорировал инструкции; введён JSON-only промпт в `_summarize_batch`, модель переключена на `gpt-5-mini`, fallback чистит префиксы и код-блоки.
- **L3=5 загадка:** UI показывал 5 сущностей при пустой базе; выяснено, что Graphiti возвращает системные/кэшированные сущности; после wipe и исправлений счётчики стабилизированы.
- **Neo4j syntax/IPv6:** `exists()` заменено на `IS NOT NULL`; URI переведён на `bolt://127.0.0.1:7687` для обхода IPv6 обрывов.
- **Reasoning Bank linkage:** `log_experience` связывает `Experience` с `Episodic` через `context_episode_id`; обновление success_rate по weighted average; добавлены `evolve_strategy` и `update_usage`.

## Процедуры тестирования
- **Смок:** `python3 scripts/run_smoke_test.py --reset` — wipe Redis/Neo4j, прогон 16 сообщений (teacher scenario), затем форензик-инспекция.
- **Инспекция:** `python3 scripts/inspect_everything.py` — вывод L1 (Redis), L2/L3 (Neo4j), Experience (count + примеры).
- **Интеграционные тесты:** `tests/integration/test_memory_v2_pipeline.py` — золотой путь 15→1, защита от гонки, каскад контекста (L0/L1).

## Решения по качеству
- **Locks:** только Redis SETNX + TTL; python-lock — доп. страховка.
- **Саммари:** JSON contract, температура 0.0, обрезка код-блоков, fallback без префиксов.
- **Сброс:** `scripts/reset_memory.py` — FLUSHALL + DETACH DELETE.
- **Наблюдаемость:** Prompt X-Ray в агенте; инспектор с точными timestamp для гонок.

## TODO / Риски
- Проверить, что UI считывает свежие статы (L1/L2) без кэша.  
- Добавить алерт, если за один прогон появляется >1 эпизод (детект гонки).
- Рассмотреть более строгий дедуп по content hash на уровне L1→L2.

