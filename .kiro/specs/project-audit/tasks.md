# Implementation Plan: Fractal Memory Project Audit

## Overview

Этот план описывает пошаговую реализацию системы аудита проекта Fractal Memory. Каждая задача строится на предыдущих и заканчивается интеграцией всех компонентов.

---

## Phase 1: Infrastructure and Core Models

- [x] 1. Set up audit infrastructure
  - Create `audit/` directory structure
  - Set up logging and configuration
  - Create base classes for checkers and testers
  - _Requirements: All_

- [x] 1.1 Create audit directory structure
  - Create `fractal_memory/audit/__init__.py`
  - Create `fractal_memory/audit/core/` for base classes
  - Create `fractal_memory/audit/checkers/` for static analysis
  - Create `fractal_memory/audit/testers/` for runtime tests
  - Create `fractal_memory/audit/reports/` for report generation
  - _Requirements: All_

- [x] 1.2 Implement core data models
  - Create `audit/core/models.py` with Issue, TestResult, Neo4jSchema dataclasses
  - Add severity levels (critical, high, medium, low)
  - Add category types (architecture, imports, schema, api, etc.)
  - _Requirements: All_

- [x] 1.3 Create base checker class
  - Create `audit/core/base_checker.py` with BaseChecker abstract class
  - Implement `run()` method template
  - Add error handling and timeout support
  - _Requirements: All_

- [x] 1.4 Set up audit configuration
  - Create `audit/config.py` with AuditConfig dataclass
  - Add paths to project files
  - Add Neo4j/Redis connection settings
  - Add timeout and parallel execution settings
  - _Requirements: 6.1, 6.2, 6.3_

---

## Phase 2: Static Analysis Components

- [x] 2. Implement static analysis checkers
  - Import checker
  - Schema validator
  - API validator
  - _Requirements: 2, 3, 4_

- [x] 2.1 Implement ImportChecker
  - Create `audit/checkers/import_checker.py`
  - Implement `check_python_imports()` using ast module
  - Implement `check_typescript_imports()` using regex/ts parser
  - Implement `find_circular_dependencies()` using graph traversal
  - Implement `check_version_compatibility()` using pkg_resources
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2.2 Write property test for ImportChecker
  - **Property 1: Import completeness**
  - **Validates: Requirements 2.1, 2.2**
  - Test that all imports in test files are validated correctly
  - Use hypothesis to generate random import statements

- [x] 2.3 Implement SchemaValidator
  - Create `audit/checkers/schema_validator.py`
  - Implement `get_actual_schema()` to query Neo4j for actual schema
  - Implement `validate_cypher_queries()` to parse Cypher and check fields
  - Implement `check_node_labels()` to verify label usage
  - Implement `check_relationships()` to verify relationship types
  - Implement `check_indexes()` to verify index existence
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 2.4 Write property test for SchemaValidator
  - **Property 2: Schema consistency**
  - **Validates: Requirements 3.1, 3.2**
  - Test that all Cypher queries reference valid fields
  - Use hypothesis to generate random Cypher queries

- [x] 2.5 Implement APIValidator
  - Create `audit/checkers/api_validator.py`
  - Implement `check_search_result_format()` to verify SearchResult consistency
  - Implement `check_memory_api()` to verify FractalMemory API
  - Implement `check_retriever_api()` to verify HybridRetriever API
  - Implement `check_fastapi_endpoints()` to verify FastAPI response formats
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 2.6 Write property test for APIValidator
  - **Property 3: API compatibility**
  - **Validates: Requirements 4.1, 4.2, 4.3**
  - Test that data structures are compatible between components
  - Use hypothesis to generate random data structures

---

## Phase 3: Runtime Analysis Components

- [x] 3. Implement runtime testers
  - Memory tester
  - Retrieval tester
  - Learning tester
  - _Requirements: 7, 8, 9_

- [x] 3.1 Implement MemoryTester
  - Create `audit/testers/memory_tester.py`
  - Implement `test_l0_to_l1_consolidation()` with real Redis
  - Implement `test_l1_to_l2_consolidation()` with real Neo4j
  - Implement `test_decay_logic()` to verify importance decreases
  - Implement `test_garbage_collection()` to verify safe deletion
  - Implement `test_deduplication()` to verify no duplicates in L2
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 3.2 Write property test for MemoryTester
  - **Property 4: Consolidation correctness**
  - **Validates: Requirements 7.1, 7.2**
  - Test that high-importance items move to higher levels
  - Use hypothesis to generate random memory items

- [x] 3.3 Write property test for decay
  - **Property 5: Decay monotonicity**
  - **Validates: Requirements 7.3**
  - Test that importance never increases without access
  - Use hypothesis to generate random time intervals

- [x] 3.4 Implement RetrievalTester
  - Create `audit/testers/retrieval_tester.py`
  - Implement `test_vector_search()` with real Graphiti
  - Implement `test_keyword_search()` with real Neo4j fulltext index
  - Implement `test_graph_search()` with real graph traversal
  - Implement `test_l0_l1_search()` with real Redis
  - Implement `test_rrf_fusion()` to verify result merging
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 3.5 Write property test for RetrievalTester
  - **Property 6: Search completeness**
  - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
  - Test that search returns results from all levels
  - Use hypothesis to generate random queries

- [x] 3.6 Implement LearningTester
  - Create `audit/testers/learning_tester.py`
  - Implement `test_strategy_creation()` to verify :Strategy nodes
  - Implement `test_experience_logging()` to verify :Experience nodes
  - Implement `test_confidence_update()` to verify success_rate updates
  - Implement `test_strategy_retrieval()` to verify get_strategies()
  - Implement `test_agent_integration()` to verify agent uses strategies
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 3.7 Write property test for LearningTester
  - **Property 7: Strategy persistence**
  - **Validates: Requirements 9.1, 9.2, 9.3**
  - Test that strategies persist and update correctly
  - Use hypothesis to generate random strategies

---

## Phase 4: Integration Analysis Components

- [ ] 4. Implement integration validators
  - E2E flow validator
  - Frontend validator
  - Config validator
  - _Requirements: 1, 6, 10_

- [x] 4.1 Implement E2EFlowValidator
  - Create `audit/testers/e2e_validator.py`
  - Implement `test_chat_flow()` to test full message cycle
  - Implement `test_memory_persistence()` to test data survives restart
  - Implement `test_learning_flow()` to test strategy usage in chat
  - _Requirements: 1.2, 1.3, 1.4_

- [ ] 4.2 Write property test for E2EFlowValidator
  - **Property 8: E2E data flow**
  - **Validates: Requirements 1.2, 1.3, 1.4**
  - Test that data flows through all stages
  - Use hypothesis to generate random messages

- [ ] 4.3 Write property test for user isolation
  - **Property 9: User isolation**
  - **Validates: Requirements 1.5**
  - Test that different users' data doesn't mix
  - Use hypothesis to generate random user IDs

- [x] 4.4 Implement FrontendValidator
  - Create `audit/checkers/frontend_validator.py`
  - Implement `check_api_types()` to compare TypeScript types with FastAPI models
  - Implement `check_cors_config()` to verify CORS settings
  - Implement `check_error_handling()` to verify error handling in React
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 4.5 Write property test for FrontendValidator
  - **Property 10: Frontend-Backend contract**
  - **Validates: Requirements 10.1, 10.2, 10.3**
  - Test that API responses match TypeScript types
  - Use hypothesis to generate random API responses

- [x] 4.6 Implement ConfigValidator
  - Create `audit/checkers/config_validator.py`
  - Implement `check_env_variables()` to verify .env completeness
  - Implement `check_docker_compose()` to verify docker-compose.yml
  - Implement `check_migrations()` to verify migrations are applied
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

---

## Phase 5: Report Generation

- [ ] 5. Implement report generation
  - Report generator
  - CLI interface
  - _Requirements: All_

- [x] 5.1 Implement ReportGenerator
  - Create `audit/reports/generator.py`
  - Implement `generate_markdown_report()` with issue categorization
  - Implement `generate_json_report()` for machine processing
  - Implement `generate_recommendations()` based on issue patterns
  - Add severity-based sorting and filtering
  - _Requirements: All_

- [x] 5.2 Create CLI interface
  - Create `audit/main.py` with argparse
  - Add `--full` flag for complete audit
  - Add `--static-only` flag for static analysis only
  - Add `--runtime-only` flag for runtime tests only
  - Add `--output-format` flag (markdown/json)
  - Add `--output-file` flag for report destination
  - _Requirements: All_

- [x] 5.3 Implement audit orchestrator
  - Create `audit/orchestrator.py`
  - Implement parallel execution of independent checks
  - Implement error handling and graceful degradation
  - Implement timeout handling for each check
  - Implement resource cleanup (close connections)
  - _Requirements: All_

---

## Phase 6: Testing and Documentation

- [ ] 6. Test and document the audit system
  - Unit tests for all components
  - Integration tests with real databases
  - Documentation and examples
  - _Requirements: All_

- [ ] 6.1 Write unit tests for all checkers
  - Test ImportChecker with mock files
  - Test SchemaValidator with mock Neo4j
  - Test APIValidator with mock components
  - Test ConfigValidator with mock configs
  - _Requirements: All_

- [ ] 6.2 Write integration tests for all testers
  - Test MemoryTester with real Neo4j + Redis
  - Test RetrievalTester with real Graphiti
  - Test LearningTester with real ReasoningBank
  - Test E2EFlowValidator with full stack
  - _Requirements: All_

- [x] 6.3 Create audit documentation
  - Write README.md for audit system
  - Document each checker and tester
  - Add usage examples
  - Add troubleshooting guide
  - _Requirements: All_

- [x] 6.4 Create example audit reports
  - Run audit on current codebase
  - Generate sample markdown report
  - Generate sample JSON report
  - Document common issues and fixes
  - _Requirements: All_

---

## Phase 7: CI/CD Integration

- [ ] 7. Integrate audit into CI/CD
  - GitHub Actions workflow
  - Automated reporting
  - _Requirements: All_

- [ ] 7.1 Create GitHub Actions workflow
  - Create `.github/workflows/audit.yml`
  - Set up Neo4j and Redis services
  - Run full audit on push/PR
  - Upload audit report as artifact
  - _Requirements: All_

- [ ] 7.2 Add audit status badge
  - Generate badge based on audit results
  - Add badge to README.md
  - Configure badge to show critical/high issue count
  - _Requirements: All_

---

## Final Checkpoint

- [x] 8. Final validation and deployment
  - Ensure all tests pass
  - Ask the user if questions arise
  - _Requirements: All_

---

## Notes

- Все задачи являются обязательными для comprehensive аудита
- Каждая задача должна завершаться работающим кодом
- После каждой фазы рекомендуется запускать аудит на текущем состоянии проекта
- Критические проблемы должны исправляться сразу после обнаружения
