# Design Document: Fractal Memory Project Audit

## Overview

Этот документ описывает дизайн системы глубокого аудита проекта Fractal Memory. Аудит будет проводиться в несколько этапов, каждый из которых проверяет определённый аспект системы. Результатом будет детальный отчёт со всеми найденными проблемами, их приоритетами и рекомендациями по исправлению.

## Architecture

### Компоненты аудита

```
┌─────────────────────────────────────────────────────────────┐
│                    AUDIT ORCHESTRATOR                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Static Analysis Layer                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  Import    │  │   Schema   │  │    API     │     │   │
│  │  │  Checker   │  │  Validator │  │  Validator │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Runtime Analysis Layer                   │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  Memory    │  │  Retrieval │  │  Learning  │     │   │
│  │  │  Tester    │  │   Tester   │  │   Tester   │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Integration Analysis Layer               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  E2E Flow  │  │  Frontend  │  │   Config   │     │   │
│  │  │  Validator │  │  Validator │  │  Validator │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Report Generator                     │   │
│  │  - Markdown отчёт с приоритетами                     │   │
│  │  - JSON для автоматической обработки                 │   │
│  │  - Рекомендации по исправлению                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Этапы аудита

1. **Static Analysis** - анализ кода без запуска
   - Проверка импортов
   - Проверка схемы данных
   - Проверка API консистентности

2. **Runtime Analysis** - анализ с запуском тестов
   - Тестирование памяти (L0→L1→L2→L3)
   - Тестирование поиска
   - Тестирование самообучения

3. **Integration Analysis** - анализ интеграции компонентов
   - E2E flow тестирование
   - Frontend-Backend интеграция
   - Конфигурация и окружение

4. **Report Generation** - генерация отчёта
   - Сводка проблем по приоритетам
   - Детальное описание каждой проблемы
   - Рекомендации по исправлению

## Components and Interfaces

### 1. Import Checker

**Назначение:** Проверка всех импортов в Python и TypeScript файлах.

**Интерфейс:**
```python
class ImportChecker:
    def check_python_imports(self, file_path: str) -> List[ImportIssue]
    def check_typescript_imports(self, file_path: str) -> List[ImportIssue]
    def find_circular_dependencies(self, root_dir: str) -> List[CircularDependency]
    def check_version_compatibility(self) -> List[VersionIssue]
```

**Проверки:**
- Существование импортируемых модулей
- Правильность относительных путей
- Циклические зависимости
- Совместимость версий библиотек

### 2. Schema Validator

**Назначение:** Проверка что код работает с реальной схемой Neo4j.

**Интерфейс:**
```python
class SchemaValidator:
    def get_actual_schema(self) -> Neo4jSchema
    def validate_cypher_queries(self, file_path: str) -> List[SchemaIssue]
    def check_node_labels(self) -> List[LabelIssue]
    def check_relationships(self) -> List[RelationshipIssue]
    def check_indexes(self) -> List[IndexIssue]
```

**Проверки:**
- Обращения к несуществующим полям
- Использование правильных меток узлов
- Использование правильных типов связей
- Наличие необходимых индексов

### 3. API Validator

**Назначение:** Проверка консистентности API между компонентами.

**Интерфейс:**
```python
class APIValidator:
    def check_search_result_format(self) -> List[APIIssue]
    def check_memory_api(self) -> List[APIIssue]
    def check_retriever_api(self) -> List[APIIssue]
    def check_fastapi_endpoints(self) -> List[APIIssue]
```

**Проверки:**
- Согласованность структур данных (SearchResult, MemoryItem и т.д.)
- Совместимость методов между компонентами
- Правильность форматов FastAPI эндпоинтов

### 4. Memory Tester

**Назначение:** Тестирование логики памяти (консолидация, decay, GC).

**Интерфейс:**
```python
class MemoryTester:
    async def test_l0_to_l1_consolidation(self) -> TestResult
    async def test_l1_to_l2_consolidation(self) -> TestResult
    async def test_decay_logic(self) -> TestResult
    async def test_garbage_collection(self) -> TestResult
    async def test_deduplication(self) -> TestResult
```

**Проверки:**
- Данные перемещаются между уровнями
- Importance уменьшается со временем
- Старые данные удаляются безопасно
- Дубликаты не создаются

### 5. Retrieval Tester

**Назначение:** Тестирование поиска на всех уровнях.

**Интерфейс:**
```python
class RetrievalTester:
    async def test_vector_search(self) -> TestResult
    async def test_keyword_search(self) -> TestResult
    async def test_graph_search(self) -> TestResult
    async def test_l0_l1_search(self) -> TestResult
    async def test_rrf_fusion(self) -> TestResult
```

**Проверки:**
- Vector search возвращает релевантные результаты
- Keyword search работает с fulltext индексом
- Graph search обходит связи правильно
- RRF fusion объединяет результаты корректно

### 6. Learning Tester

**Назначение:** Тестирование ReasoningBank и самообучения.

**Интерфейс:**
```python
class LearningTester:
    async def test_strategy_creation(self) -> TestResult
    async def test_experience_logging(self) -> TestResult
    async def test_confidence_update(self) -> TestResult
    async def test_strategy_retrieval(self) -> TestResult
    async def test_agent_integration(self) -> TestResult
```

**Проверки:**
- Стратегии создаются в Neo4j
- Опыт логируется правильно
- Confidence обновляется при использовании
- Агент использует стратегии в промпте

### 7. E2E Flow Validator

**Назначение:** Проверка полного цикла работы системы.

**Интерфейс:**
```python
class E2EFlowValidator:
    async def test_chat_flow(self) -> TestResult
    async def test_memory_persistence(self) -> TestResult
    async def test_learning_flow(self) -> TestResult
```

**Проверки:**
- Полный цикл: сообщение → поиск → ответ → сохранение → обучение
- Данные сохраняются на всех уровнях
- Система восстанавливается после перезапуска

### 8. Frontend Validator

**Назначение:** Проверка интеграции React frontend с FastAPI backend.

**Интерфейс:**
```python
class FrontendValidator:
    def check_api_types(self) -> List[TypeIssue]
    def check_cors_config(self) -> List[CORSIssue]
    def check_error_handling(self) -> List[ErrorHandlingIssue]
```

**Проверки:**
- TypeScript типы совпадают с FastAPI моделями
- CORS настроен правильно
- Ошибки обрабатываются корректно

### 9. Config Validator

**Назначение:** Проверка конфигурации и окружения.

**Интерфейс:**
```python
class ConfigValidator:
    def check_env_variables(self) -> List[ConfigIssue]
    def check_docker_compose(self) -> List[DockerIssue]
    def check_migrations(self) -> List[MigrationIssue]
```

**Проверки:**
- Все обязательные переменные установлены
- Docker compose настроен правильно
- Миграции применены

### 10. Report Generator

**Назначение:** Генерация детального отчёта.

**Интерфейс:**
```python
class ReportGenerator:
    def generate_markdown_report(self, issues: List[Issue]) -> str
    def generate_json_report(self, issues: List[Issue]) -> dict
    def generate_recommendations(self, issues: List[Issue]) -> List[Recommendation]
```

**Формат отчёта:**
```markdown
# Fractal Memory Project Audit Report

## Executive Summary
- Total issues found: X
- Critical: Y
- High: Z
- Medium: W
- Low: V

## Issues by Category

### 1. Architecture Issues
- [CRITICAL] Issue description
  - Location: file.py:123
  - Impact: ...
  - Recommendation: ...

### 2. Import Issues
...

## Recommendations
1. Fix critical issues first
2. ...
```

## Data Models

### Issue

```python
@dataclass
class Issue:
    id: str
    category: str  # "architecture", "imports", "schema", "api", etc.
    severity: str  # "critical", "high", "medium", "low"
    title: str
    description: str
    location: str  # file:line
    impact: str
    recommendation: str
    code_snippet: Optional[str] = None
```

### TestResult

```python
@dataclass
class TestResult:
    test_name: str
    passed: bool
    issues: List[Issue]
    duration_ms: float
    details: Dict[str, Any]
```

### Neo4jSchema

```python
@dataclass
class Neo4jSchema:
    node_labels: Dict[str, List[str]]  # label -> [field1, field2, ...]
    relationships: List[Tuple[str, str, str]]  # (from_label, rel_type, to_label)
    indexes: List[str]
    constraints: List[str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Import completeness
*For any* Python or TypeScript file in the project, all imported modules should exist and be accessible
**Validates: Requirements 2.1, 2.2**

### Property 2: Schema consistency
*For any* Cypher query in the codebase, all referenced node fields should exist in the actual Neo4j schema
**Validates: Requirements 3.1, 3.2**

### Property 3: API compatibility
*For any* two components that exchange data, the data structures should be compatible (same fields, same types)
**Validates: Requirements 4.1, 4.2, 4.3**

### Property 4: Consolidation correctness
*For any* memory item with high importance, after consolidation it should be present on a higher level and removed from the lower level
**Validates: Requirements 7.1, 7.2**

### Property 5: Decay monotonicity
*For any* memory item, its importance should never increase over time without explicit access
**Validates: Requirements 7.3**

### Property 6: Search completeness
*For any* query, the search should return results from all configured levels (L0, L1, L2, L3)
**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 7: Strategy persistence
*For any* created strategy, it should be retrievable from Neo4j and its confidence should update on usage
**Validates: Requirements 9.1, 9.2, 9.3**

### Property 8: E2E data flow
*For any* user message, the data should flow through all stages: receive → search → respond → save → learn
**Validates: Requirements 1.2, 1.3, 1.4**

### Property 9: User isolation
*For any* two different users, their data should not be mixed (no cross-user data leakage)
**Validates: Requirements 1.5**

### Property 10: Frontend-Backend contract
*For any* API endpoint, the response format should match the TypeScript types in the frontend
**Validates: Requirements 10.1, 10.2, 10.3**

## Error Handling

### Graceful Degradation

Если какой-то компонент аудита падает, остальные должны продолжить работу:

```python
async def run_audit():
    results = []
    for checker in checkers:
        try:
            result = await checker.run()
            results.append(result)
        except Exception as e:
            logger.error(f"Checker {checker.name} failed: {e}")
            results.append(TestResult(
                test_name=checker.name,
                passed=False,
                issues=[Issue(
                    category="audit_failure",
                    severity="high",
                    title=f"Audit checker failed: {checker.name}",
                    description=str(e),
                    ...
                )],
                ...
            ))
    return results
```

### Timeout Handling

Каждый тест должен иметь таймаут, чтобы не зависнуть:

```python
async def run_test_with_timeout(test_func, timeout_seconds=30):
    try:
        return await asyncio.wait_for(test_func(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return TestResult(
            test_name=test_func.__name__,
            passed=False,
            issues=[Issue(
                category="timeout",
                severity="medium",
                title=f"Test timed out: {test_func.__name__}",
                ...
            )],
            ...
        )
```

## Testing Strategy

### Unit Tests

Каждый компонент аудита должен иметь unit тесты:

```python
# test_import_checker.py
def test_import_checker_finds_missing_module():
    checker = ImportChecker()
    issues = checker.check_python_imports("test_file_with_bad_import.py")
    assert len(issues) > 0
    assert issues[0].category == "imports"
    assert "module not found" in issues[0].description.lower()
```

### Integration Tests

Тесты должны работать с реальным Neo4j и Redis:

```python
# test_memory_tester.py
@pytest.mark.integration
async def test_memory_consolidation_with_real_db():
    tester = MemoryTester(neo4j_uri="...", redis_url="...")
    result = await tester.test_l0_to_l1_consolidation()
    assert result.passed
    assert len(result.issues) == 0
```

### Property-Based Tests

Для проверки свойств используем hypothesis:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1), st.floats(min_value=0.0, max_value=1.0))
async def test_memory_item_importance_never_increases_without_access(content, initial_importance):
    """Property 5: Decay monotonicity"""
    memory = FractalMemory(config)
    await memory.initialize()
    
    item_id = await memory.remember(content, importance=initial_importance)
    
    # Wait for decay
    await asyncio.sleep(1)
    await memory._apply_decay()
    
    # Get item
    stats = await memory.get_stats()
    # Check that importance didn't increase
    # (implementation depends on how we can access individual items)
```

## Performance Considerations

### Parallel Execution

Независимые проверки должны выполняться параллельно:

```python
async def run_static_analysis():
    tasks = [
        import_checker.run(),
        schema_validator.run(),
        api_validator.run(),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Caching

Результаты дорогих операций (например, получение схемы Neo4j) должны кэшироваться:

```python
class SchemaValidator:
    def __init__(self):
        self._schema_cache = None
    
    async def get_actual_schema(self):
        if self._schema_cache is None:
            self._schema_cache = await self._fetch_schema_from_neo4j()
        return self._schema_cache
```

### Resource Cleanup

Все соединения должны закрываться после аудита:

```python
async def run_audit():
    try:
        # Run all checks
        results = await run_all_checks()
    finally:
        # Cleanup
        await memory.close()
        await neo4j_driver.close()
        await redis_client.close()
```

## Deployment

### CLI Interface

Аудит должен запускаться через CLI:

```bash
# Полный аудит
python -m audit.main --full

# Только статический анализ
python -m audit.main --static-only

# Только runtime тесты
python -m audit.main --runtime-only

# Генерация отчёта в JSON
python -m audit.main --output-format json --output-file audit_report.json
```

### CI/CD Integration

Аудит должен интегрироваться в CI/CD:

```yaml
# .github/workflows/audit.yml
name: Project Audit
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run audit
        run: |
          docker compose up -d neo4j redis
          python -m audit.main --full --output-format json --output-file audit_report.json
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: audit-report
          path: audit_report.json
```

## Future Enhancements

1. **Automated Fixes** - автоматическое исправление простых проблем (например, добавление отсутствующих импортов)
2. **Trend Analysis** - отслеживание изменений количества проблем со временем
3. **Custom Rules** - возможность добавлять пользовательские правила проверки
4. **Interactive Mode** - интерактивный режим для исправления проблем по одной
5. **Performance Profiling** - профилирование производительности критических путей
