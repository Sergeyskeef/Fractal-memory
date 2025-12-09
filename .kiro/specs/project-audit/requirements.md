# Requirements Document: Fractal Memory Project Audit

## Introduction

Этот документ описывает требования к глубокому аудиту проекта Fractal Memory. Цель аудита — найти все проблемы в существующей реализации: неработающие импорты, нарушенные связи между компонентами, несоответствия между задуманной и реальной архитектурой многоуровневой памяти (L0→L1→L2→L3), а также любые другие проблемы, которые могут помешать корректной работе системы.

## Glossary

- **System**: Fractal Memory — система иерархической памяти для AI-агента
- **L0**: Working Memory — кратковременная память (секунды-минуты), хранится в Python list + Redis Streams
- **L1**: Short-Term Memory — краткосрочная память (минуты-часы), хранится в Python dict + Redis
- **L2**: Medium-Term Memory — среднесрочная память (дни-недели), хранится в Neo4j через Graphiti (Episodic nodes)
- **L3**: Long-Term Memory — долговременная память (месяцы-годы), хранится в Neo4j через Graphiti (Entity nodes)
- **Graphiti**: Библиотека для работы с графом знаний, используется для L2/L3
- **GraphitiStore**: Обёртка над Graphiti для работы с Neo4j
- **RedisMemoryStore**: Хранилище для L0/L1 на Redis Streams
- **FractalMemory**: Главный класс памяти, координирует все уровни
- **FractalAgent**: AI-агент, использующий FractalMemory
- **HybridRetriever**: Компонент для гибридного поиска (vector + keyword + graph)
- **ReasoningBank**: Компонент для самообучения на опыте
- **Consolidation**: Процесс перемещения важной информации с нижних уровней на верхние (L0→L1→L2→L3)
- **Decay**: Процесс забывания неважной информации
- **Episode**: Эпизод памяти в Neo4j (узел :Episodic)
- **Entity**: Сущность в Neo4j (узел :Entity)
- **Strategy**: Стратегия решения задач в ReasoningBank (узел :Strategy)

## Requirements

### Requirement 1: Архитектурная целостность

**User Story:** Как разработчик, я хочу убедиться что архитектура памяти реализована согласно документации, чтобы система работала как задумано.

#### Acceptance Criteria

1. WHEN проверяется структура уровней памяти THEN System SHALL подтвердить что L0/L1 используют Redis, а L2/L3 используют Neo4j через Graphiti
2. WHEN проверяется консолидация THEN System SHALL подтвердить что данные перемещаются L0→L1→L2→L3 согласно importance и access_count
3. WHEN проверяется decay THEN System SHALL подтвердить что неважная информация забывается на всех уровнях
4. WHEN проверяется интеграция компонентов THEN System SHALL подтвердить что FractalMemory, GraphitiStore, RedisMemoryStore работают согласованно
5. WHEN проверяется user isolation THEN System SHALL подтвердить что данные разных пользователей изолированы через user_id/user_tag

### Requirement 2: Импорты и зависимости

**User Story:** Как разработчик, я хочу найти все неработающие импорты и неправильные зависимости, чтобы код компилировался без ошибок.

#### Acceptance Criteria

1. WHEN проверяются импорты в Python файлах THEN System SHALL найти все несуществующие модули или классы
2. WHEN проверяются относительные импорты THEN System SHALL найти все неправильные пути (например, импорт удалённого graphiti_adapter)
3. WHEN проверяются циклические зависимости THEN System SHALL найти все циклы в импортах
4. WHEN проверяются версии библиотек THEN System SHALL найти несовместимости между graphiti-core, neo4j-driver и другими зависимостями
5. WHEN проверяется TypeScript frontend THEN System SHALL найти все неработающие импорты в React компонентах

### Requirement 3: Схема данных Neo4j

**User Story:** Как разработчик, я хочу убедиться что код работает с реальной схемой Neo4j, чтобы не было ошибок при обращении к несуществующим полям.

#### Acceptance Criteria

1. WHEN проверяются Cypher запросы THEN System SHALL найти все обращения к несуществующим полям узлов (например, deleted, importance_score, user_id в Episodic)
2. WHEN проверяются метки узлов THEN System SHALL подтвердить что используются правильные метки (:Episodic, :Entity, :Strategy, :Experience)
3. WHEN проверяются связи THEN System SHALL подтвердить что используются правильные типы связей (HAS_ENTITY, RELATES_TO и т.д.)
4. WHEN проверяются индексы THEN System SHALL подтвердить что все необходимые индексы созданы миграциями
5. WHEN проверяется user_tag THEN System SHALL подтвердить что фильтрация по пользователю работает через [user:<id>] в content

### Requirement 4: Консистентность API

**User Story:** Как разработчик, я хочу убедиться что все компоненты используют согласованные интерфейсы, чтобы не было ошибок при вызове методов.

#### Acceptance Criteria

1. WHEN проверяется SearchResult THEN System SHALL подтвердить что все компоненты используют одинаковую структуру (content, score, source, metadata)
2. WHEN проверяется GraphitiStore.search() THEN System SHALL подтвердить что возвращаемый формат совместим с HybridRetriever
3. WHEN проверяется RedisMemoryStore THEN System SHALL подтвердить что API методов (l0_add, l1_add_session) используются правильно
4. WHEN проверяется FractalMemory THEN System SHALL подтвердить что методы remember/recall/consolidate работают согласованно
5. WHEN проверяется FastAPI backend THEN System SHALL подтвердить что эндпоинты возвращают правильные форматы данных

### Requirement 5: Тесты и покрытие

**User Story:** Как разработчик, я хочу найти все проблемы в тестах, чтобы они проверяли реальную функциональность.

#### Acceptance Criteria

1. WHEN проверяются unit тесты THEN System SHALL найти все тесты, которые используют устаревшие API или mock'и
2. WHEN проверяются интеграционные тесты THEN System SHALL найти все тесты, которые не работают с реальным Neo4j/Redis
3. WHEN проверяется покрытие THEN System SHALL найти все некрытые критические пути (консолидация, decay, GC)
4. WHEN проверяются fixtures THEN System SHALL найти все проблемы в conftest.py (например, неправильная инициализация)
5. WHEN проверяются assertions THEN System SHALL найти все тесты с неправильными ожиданиями (например, проверка несуществующих полей)

### Requirement 6: Конфигурация и окружение

**User Story:** Как разработчик, я хочу убедиться что конфигурация системы корректна, чтобы не было проблем при запуске.

#### Acceptance Criteria

1. WHEN проверяется .env THEN System SHALL найти все отсутствующие обязательные переменные (NEO4J_PASSWORD, OPENAI_API_KEY)
2. WHEN проверяется docker-compose.yml THEN System SHALL найти все проблемы с портами, volumes, зависимостями
3. WHEN проверяется backend/config.py THEN System SHALL найти все несоответствия между Settings и реальным использованием
4. WHEN проверяются миграции THEN System SHALL подтвердить что все миграции применены и схема актуальна
5. WHEN проверяется frontend THEN System SHALL найти все проблемы с CORS, API_URL, переменными окружения

### Requirement 7: Логика консолидации и decay

**User Story:** Как разработчик, я хочу убедиться что консолидация и decay работают правильно, чтобы память не переполнялась и важные данные не терялись.

#### Acceptance Criteria

1. WHEN проверяется L0→L1 консолидация THEN System SHALL подтвердить что данные сохраняются в Redis и удаляются из L0
2. WHEN проверяется L1→L2 консолидация THEN System SHALL подтвердить что данные сохраняются в Neo4j через Graphiti и удаляются из L1
3. WHEN проверяется decay THEN System SHALL подтвердить что importance уменьшается со временем на всех уровнях
4. WHEN проверяется дедупликация THEN System SHALL подтвердить что _is_duplicate_in_l2 работает правильно
5. WHEN проверяется garbage collection THEN System SHALL подтвердить что старые данные удаляются безопасно с учётом retention policies

### Requirement 8: Поиск и retrieval

**User Story:** Как разработчик, я хочу убедиться что поиск работает на всех уровнях памяти, чтобы агент находил релевантную информацию.

#### Acceptance Criteria

1. WHEN проверяется vector search THEN System SHALL подтвердить что Graphiti embeddings работают и возвращают релевантные результаты
2. WHEN проверяется keyword search THEN System SHALL подтвердить что fulltext индекс Neo4j работает
3. WHEN проверяется graph search THEN System SHALL подтвердить что обход связей работает правильно
4. WHEN проверяется L0/L1 search THEN System SHALL подтвердить что поиск в Redis работает
5. WHEN проверяется RRF fusion THEN System SHALL подтвердить что результаты из разных источников объединяются правильно

### Requirement 9: ReasoningBank и самообучение

**User Story:** Как разработчик, я хочу убедиться что ReasoningBank работает правильно, чтобы агент учился на опыте.

#### Acceptance Criteria

1. WHEN проверяется создание стратегий THEN System SHALL подтвердить что узлы :Strategy создаются в Neo4j
2. WHEN проверяется логирование опыта THEN System SHALL подтвердить что узлы :Experience создаются и связываются со стратегиями
3. WHEN проверяется обновление confidence THEN System SHALL подтвердить что success_rate обновляется при использовании стратегии
4. WHEN проверяется получение стратегий THEN System SHALL подтвердить что get_strategies возвращает релевантные стратегии для task_type
5. WHEN проверяется интеграция с агентом THEN System SHALL подтвердить что агент использует стратегии в промпте

### Requirement 10: Frontend и API

**User Story:** Как разработчик, я хочу убедиться что frontend корректно работает с backend API, чтобы пользователь мог взаимодействовать с системой.

#### Acceptance Criteria

1. WHEN проверяется /chat эндпоинт THEN System SHALL подтвердить что формат ChatResponse совпадает с ожиданиями frontend
2. WHEN проверяется /memory/stats THEN System SHALL подтвердить что возвращаются правильные счётчики для всех уровней
3. WHEN проверяется /memory/{level} THEN System SHALL подтвердить что возвращаются узлы памяти в формате MemoryNode[]
4. WHEN проверяется CORS THEN System SHALL подтвердить что frontend может делать запросы к backend
5. WHEN проверяется обработка ошибок THEN System SHALL подтвердить что ошибки API правильно обрабатываются в React компонентах
