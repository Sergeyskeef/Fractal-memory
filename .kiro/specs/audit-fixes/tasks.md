# Implementation Tasks: Fixing Fractal Memory Audit Issues

## Overview

This document provides a step-by-step implementation plan for fixing the 57 real issues found in the Fractal Memory audit. Tasks are organized by priority and dependencies.

---

## Phase 1: Critical Import Issues (MUST DO FIRST)

### Task 1.1: Fix FractalMemory Module Import
**Priority:** Critical 🔴  
**Estimated Time:** 1-2 hours  
**Dependencies:** None  
**Requirements:** User Story 1.1

- [ ] 1.1.1 Investigate current module structure
  - Run `ls -la fractal_memory/src/` to see files
  - Check if `fractal_memory.py` or similar exists
  - Read current `src/__init__.py` to see what's exported

- [ ] 1.1.2 Identify main classes to export
  - FractalMemory (main memory interface)
  - GraphitiStore (Neo4j integration)
  - RedisMemoryStore (Redis integration)
  - Any other public classes

- [ ] 1.1.3 Update `src/__init__.py`
  - Add imports for all public classes
  - Add `__all__` list with exported names
  - Test import: `python -c "from fractal_memory import FractalMemory"`

- [ ] 1.1.4 Verify integration tests can import
  - Run: `python -c "from fractal_memory import FractalMemory; print('Success')"`
  - Check that E2EFlowValidator can import
  - Check that RetrievalTester can import

**Acceptance Test:**
```bash
cd fractal_memory
python -c "from fractal_memory import FractalMemory, GraphitiStore, RedisMemoryStore"
echo "Import test passed!"
```

---

### Task 1.2: Fix ReasoningBank Module Import
**Priority:** Critical 🔴  
**Estimated Time:** 1 hour  
**Dependencies:** None  
**Requirements:** User Story 1.2

- [ ] 1.2.1 Locate ReasoningBank code
  - Search for ReasoningBank class: `find . -name "*.py" -exec grep -l "class ReasoningBank" {} \;`
  - Identify correct module path

- [ ] 1.2.2 Update imports if needed
  - If in `src/`, add to `src/__init__.py`
  - If in separate package, verify package structure

- [ ] 1.2.3 Test import
  - Run: `python -c "from reasoning_bank import ReasoningBank"`
  - Or: `python -c "from fractal_memory.reasoning_bank import ReasoningBank"`

**Acceptance Test:**
```bash
cd fractal_memory
python -c "from reasoning_bank import ReasoningBank" || python -c "from fractal_memory.reasoning_bank import ReasoningBank"
echo "ReasoningBank import test passed!"
```

---

### Task 1.3: Re-run Audit After Import Fixes
**Priority:** Critical 🔴  
**Estimated Time:** 15 minutes  
**Dependencies:** Tasks 1.1, 1.2  
**Requirements:** All Phase 1

- [ ] 1.3.1 Run full audit
  ```bash
  cd fractal_memory
  python -m audit.main --full --output-file audit_reports/audit_after_imports.md
  ```

- [ ] 1.3.2 Verify import issues are resolved
  - Check that E2EFlowValidator can run
  - Check that RetrievalTester can run
  - Note any new issues discovered

- [ ] 1.3.3 Document results
  - Compare issue count before/after
  - Update progress tracking

---

## Phase 2: Critical Schema Issues

### Task 2.1: Investigate Strategy Node Schema
**Priority:** Critical 🔴  
**Estimated Time:** 30 minutes  
**Dependencies:** None  
**Requirements:** User Story 2.1

- [ ] 2.1.1 Query actual Strategy schema
  ```cypher
  MATCH (s:Strategy)
  RETURN keys(s) LIMIT 1
  ```

- [ ] 2.1.2 Query sample Strategy node
  ```cypher
  MATCH (s:Strategy)
  RETURN s LIMIT 1
  ```

- [ ] 2.1.3 Document actual fields
  - Create list of all fields found
  - Note field types and example values
  - Compare with code expectations

**Expected Output:** Document with actual Strategy schema

---

### Task 2.2: Fix Strategy Field References in Code
**Priority:** Critical 🔴  
**Estimated Time:** 1-2 hours  
**Dependencies:** Task 2.1  
**Requirements:** User Story 2.1

- [ ] 2.2.1 Find all references to Strategy fields
  ```bash
  grep -r "s\.strategy" fractal_memory/src/
  grep -r "Strategy" fractal_memory/src/ | grep -E "\.(strategy|task_type|success_rate)"
  ```

- [ ] 2.2.2 Update Cypher queries
  - Replace `s.strategy` with correct field name (e.g., `s.content` or `s.description`)
  - Verify all Strategy queries use correct fields
  - Test each query in Neo4j browser

- [ ] 2.2.3 Update Python code
  - Update any Python code that accesses Strategy fields
  - Update type hints if needed
  - Update tests if needed

**Acceptance Test:**
```bash
# Run SchemaValidator
cd fractal_memory
python -c "from audit.checkers.schema_validator import SchemaValidator; v = SchemaValidator(); v.run()"
# Should show 0 Strategy field issues
```

---

### Task 2.3: Verify Episodic Node Schema
**Priority:** High 🟠  
**Estimated Time:** 1 hour  
**Dependencies:** None  
**Requirements:** User Story 2.2

- [ ] 2.3.1 Query actual Episodic schema
  ```cypher
  MATCH (e:Episodic)
  RETURN keys(e) LIMIT 1
  ```

- [ ] 2.3.2 Query sample Episodic nodes
  ```cypher
  MATCH (e:Episodic)
  RETURN e LIMIT 5
  ```

- [ ] 2.3.3 Verify critical fields exist
  - Check for: `content`, `importance_score`, `user_id`, `deleted`, `created_at`
  - Check for: `promoted_to_l2`, `access_count`, `last_accessed`
  - Document any missing fields

- [ ] 2.3.4 Update code if needed
  - Fix any field name mismatches
  - Add missing field handling
  - Update queries

**Acceptance Test:**
```bash
# Verify no Episodic field warnings in Neo4j logs
docker logs fractal_memory_neo4j 2>&1 | grep -i "property.*does not exist"
# Should be empty or not mention Episodic fields
```

---

### Task 2.4: Re-run Schema Validation
**Priority:** High 🟠  
**Estimated Time:** 15 minutes  
**Dependencies:** Tasks 2.2, 2.3  
**Requirements:** User Stories 2.1, 2.2

- [ ] 2.4.1 Run SchemaValidator
  ```bash
  cd fractal_memory
  python -m audit.main --static-only
  ```

- [ ] 2.4.2 Verify schema issues are resolved
  - Check SchemaValidator output
  - Should show 0 critical schema issues
  - Document any remaining issues

---

## Phase 3: High Priority API Issues

### Task 3.1: Create Unified Type Definitions
**Priority:** High 🟠  
**Estimated Time:** 1 hour  
**Dependencies:** None  
**Requirements:** User Story 3.1

- [ ] 3.1.1 Create `src/types.py` (if doesn't exist)
  - Define `SearchResult` dataclass/Pydantic model
  - Define other shared types
  - Add type hints and documentation

- [ ] 3.1.2 Define SearchResult structure
  ```python
  @dataclass
  class SearchResult:
      content: str
      score: float
      source: str  # "vector", "keyword", "graph", "l0", "l1"
      metadata: Dict[str, Any]
      node_id: Optional[str] = None
      timestamp: Optional[datetime] = None
  ```

- [ ] 3.1.3 Document type usage
  - Add docstrings
  - Add usage examples
  - Document field meanings

---

### Task 3.2: Update Components to Use Unified Types
**Priority:** High 🟠  
**Estimated Time:** 2-3 hours  
**Dependencies:** Task 3.1  
**Requirements:** User Stories 3.1, 3.2, 3.3

- [ ] 3.2.1 Update HybridRetriever
  - Import SearchResult from types
  - Update all search methods to return List[SearchResult]
  - Verify vector_search, keyword_search, graph_search signatures

- [ ] 3.2.2 Update FractalMemory
  - Import SearchResult from types
  - Update search() method to return List[SearchResult]
  - Verify remember(), consolidate(), get_stats() exist

- [ ] 3.2.3 Update FastAPI endpoints
  - Import SearchResult from types
  - Add response_model to all endpoints
  - Create Pydantic models for request/response

- [ ] 3.2.4 Update tests
  - Update test expectations to use SearchResult
  - Verify all tests pass

**Acceptance Test:**
```bash
cd fractal_memory
python -m audit.checkers.api_validator
# Should show 0 API consistency issues
```

---

### Task 3.3: Add FastAPI Response Models
**Priority:** Medium 🟡  
**Estimated Time:** 2 hours  
**Dependencies:** Task 3.1  
**Requirements:** User Story 3.4

- [ ] 3.3.1 Identify endpoints without response_model
  ```bash
  grep -r "@app\." fractal_memory/backend/ | grep -v "response_model"
  ```

- [ ] 3.3.2 Create Pydantic models for responses
  - Create models in `backend/models.py` or similar
  - Use SearchResult and other unified types
  - Add validation

- [ ] 3.3.3 Add response_model to endpoints
  - Update each endpoint decorator
  - Test that responses match models
  - Verify validation works

**Acceptance Test:**
```bash
# All endpoints should have response_model
grep -r "@app\." fractal_memory/backend/ | grep -v "response_model" | wc -l
# Should be 0
```

---

## Phase 4: High Priority Search Issues

### Task 4.1: Test Vector Search
**Priority:** High 🟠  
**Estimated Time:** 1 hour  
**Dependencies:** Phase 1 (imports fixed)  
**Requirements:** User Story 5.1

- [ ] 4.1.1 Run RetrievalTester for vector search
  ```bash
  cd fractal_memory
  python -c "from audit.testers.retrieval_tester import RetrievalTester; t = RetrievalTester(); t.test_vector_search()"
  ```

- [ ] 4.1.2 Verify results
  - Check that results have similarity scores
  - Verify embeddings are generated
  - Check Graphiti integration

- [ ] 4.1.3 Fix any issues found
  - Update code as needed
  - Re-test until passing

---

### Task 4.2: Test Keyword Search
**Priority:** High 🟠  
**Estimated Time:** 1 hour  
**Dependencies:** Phase 1 (imports fixed)  
**Requirements:** User Story 5.2

- [ ] 4.2.1 Verify fulltext index exists
  ```cypher
  CALL db.indexes()
  ```

- [ ] 4.2.2 Run RetrievalTester for keyword search
  ```bash
  python -c "from audit.testers.retrieval_tester import RetrievalTester; t = RetrievalTester(); t.test_keyword_search()"
  ```

- [ ] 4.2.3 Fix any issues found

---

### Task 4.3: Test Graph Search
**Priority:** High 🟠  
**Estimated Time:** 1 hour  
**Dependencies:** Phase 1 (imports fixed)  
**Requirements:** User Story 5.3

- [ ] 4.3.1 Run RetrievalTester for graph search
  ```bash
  python -c "from audit.testers.retrieval_tester import RetrievalTester; t = RetrievalTester(); t.test_graph_search()"
  ```

- [ ] 4.3.2 Verify relationship traversal
  - Check that MENTIONS relationships are followed
  - Verify Entity nodes are found
  - Check result relevance

- [ ] 4.3.3 Fix any issues found

---

### Task 4.4: Test L0/L1 Search
**Priority:** High 🟠  
**Estimated Time:** 1 hour  
**Dependencies:** Phase 1 (imports fixed)  
**Requirements:** User Story 5.4

- [ ] 4.4.1 Verify Redis has L0/L1 data
  ```bash
  redis-cli KEYS "memory:*:l0:*"
  redis-cli KEYS "memory:*:l1:*"
  ```

- [ ] 4.4.2 Run RetrievalTester for L0/L1 search
  ```bash
  python -c "from audit.testers.retrieval_tester import RetrievalTester; t = RetrievalTester(); t.test_l0_l1_search()"
  ```

- [ ] 4.4.3 Fix any issues found

---

### Task 4.5: Test RRF Fusion
**Priority:** Medium 🟡  
**Estimated Time:** 1 hour  
**Dependencies:** Tasks 4.1-4.4  
**Requirements:** User Story 5.5

- [ ] 4.5.1 Run RetrievalTester for RRF fusion
  ```bash
  python -c "from audit.testers.retrieval_tester import RetrievalTester; t = RetrievalTester(); t.test_rrf_fusion()"
  ```

- [ ] 4.5.2 Verify result merging
  - Check that results from multiple sources are combined
  - Verify scores are normalized
  - Check ranking is correct

- [ ] 4.5.3 Fix any issues found

---

## Phase 5: Medium Priority Memory Issues

### Task 5.1: Test L0→L1 Consolidation
**Priority:** Medium 🟡  
**Estimated Time:** 2 hours  
**Dependencies:** Phase 1 (imports fixed)  
**Requirements:** User Story 4.1

- [ ] 5.1.1 Create test memory items in L0
  ```python
  # Add test items to Redis L0
  # Set importance scores above threshold
  ```

- [ ] 5.1.2 Trigger consolidation
  ```python
  # Call consolidation logic
  # Or wait for automatic consolidation
  ```

- [ ] 5.1.3 Verify items moved to L1
  ```bash
  redis-cli KEYS "memory:*:l1:*"
  # Should show L1 keys
  ```

- [ ] 5.1.4 Run MemoryTester
  ```bash
  python -c "from audit.testers.memory_tester import MemoryTester; t = MemoryTester(); t.test_l0_to_l1_consolidation()"
  ```

- [ ] 5.1.5 Fix any issues found
  - Check consolidation triggers
  - Verify importance threshold
  - Check key format

---

### Task 5.2: Test L1→L2 Consolidation
**Priority:** Medium 🟡  
**Estimated Time:** 2 hours  
**Dependencies:** Task 5.1  
**Requirements:** User Story 4.2

- [ ] 5.2.1 Create test memory items in L1
  ```python
  # Add test items to Redis L1
  # Set importance scores above L2 threshold
  ```

- [ ] 5.2.2 Trigger L1→L2 consolidation
  ```python
  # Call consolidation logic
  ```

- [ ] 5.2.3 Verify items moved to Neo4j
  ```cypher
  MATCH (e:Episodic)
  WHERE e.promoted_to_l2 = true
  RETURN count(e)
  ```

- [ ] 5.2.4 Run MemoryTester
  ```bash
  python -c "from audit.testers.memory_tester import MemoryTester; t = MemoryTester(); t.test_l1_to_l2_consolidation()"
  ```

- [ ] 5.2.5 Fix any issues found
  - Check promoted_to_l2 flag is set
  - Verify data is in Neo4j
  - Check Redis keys are cleaned up

---

### Task 5.3: Test Complete Memory Lifecycle
**Priority:** Medium 🟡  
**Estimated Time:** 2 hours  
**Dependencies:** Tasks 5.1, 5.2  
**Requirements:** User Story 4.3

- [ ] 5.3.1 Create end-to-end test
  ```python
  # 1. Create memory item
  # 2. Verify in L0
  # 3. Consolidate to L1
  # 4. Verify in L1
  # 5. Consolidate to L2
  # 6. Verify in Neo4j
  # 7. Test decay
  # 8. Test retrieval at each level
  ```

- [ ] 5.3.2 Run E2EFlowValidator
  ```bash
  python -c "from audit.testers.e2e_validator import E2EFlowValidator; v = E2EFlowValidator(); v.test_memory_persistence()"
  ```

- [ ] 5.3.3 Document lifecycle behavior
  - Document timing of consolidations
  - Document importance thresholds
  - Document decay rates

---

## Phase 6: User Isolation Verification

### Task 6.1: Test User Isolation
**Priority:** High 🟠  
**Estimated Time:** 2 hours  
**Dependencies:** Phase 1 (imports fixed)  
**Requirements:** User Story 2.3

- [ ] 6.1.1 Create test data for multiple users
  ```python
  # Create memories for user1
  # Create memories for user2
  # Ensure different content
  ```

- [ ] 6.1.2 Test that users can't see each other's data
  ```python
  # Search as user1, should not see user2 data
  # Search as user2, should not see user1 data
  ```

- [ ] 6.1.3 Verify content field has user tags
  ```cypher
  MATCH (e:Episodic)
  WHERE e.content CONTAINS "[user:"
  RETURN e.content LIMIT 5
  ```

- [ ] 6.1.4 Verify queries filter by user
  - Check all Cypher queries include user filtering
  - Check Redis keys include user ID
  - Test cross-user access attempts

- [ ] 6.1.5 Add property test if needed
  - Use hypothesis to generate random user IDs
  - Test that data never leaks between users

**Acceptance Test:**
```python
# User isolation test
from fractal_memory import FractalMemory

fm = FractalMemory()
fm.remember("user1", "secret data for user1")
fm.remember("user2", "secret data for user2")

results1 = fm.search("user1", "secret")
results2 = fm.search("user2", "secret")

assert "user2" not in str(results1)
assert "user1" not in str(results2)
print("User isolation test passed!")
```

---

## Phase 7: Configuration and Environment

### Task 7.1: Verify Environment Variables
**Priority:** Low 🟢  
**Estimated Time:** 1 hour  
**Dependencies:** None  
**Requirements:** User Story 6.1

- [ ] 7.1.1 Compare .env.example with .env
  ```bash
  diff fractal_memory/.env.example fractal_memory/.env
  ```

- [ ] 7.1.2 Document all required variables
  - Create list of required vs optional
  - Add descriptions for each
  - Add example values

- [ ] 7.1.3 Add startup validation
  ```python
  # In main.py or config.py
  required_vars = ["NEO4J_URI", "REDIS_URL", ...]
  for var in required_vars:
      if not os.getenv(var):
          raise ValueError(f"Missing required env var: {var}")
  ```

- [ ] 7.1.4 Run ConfigValidator
  ```bash
  python -m audit.checkers.config_validator
  ```

---

### Task 7.2: Verify Docker Compose
**Priority:** Low 🟢  
**Estimated Time:** 1 hour  
**Dependencies:** None  
**Requirements:** User Story 6.2

- [ ] 7.2.1 Review docker-compose.yml
  - Check service definitions
  - Verify volume mounts
  - Check port mappings
  - Verify environment variables

- [ ] 7.2.2 Test Docker Compose startup
  ```bash
  cd fractal_memory
  docker-compose down
  docker-compose up -d
  docker-compose ps
  # All services should be "Up"
  ```

- [ ] 7.2.3 Test service connectivity
  ```bash
  # Test Neo4j
  curl http://localhost:7474
  
  # Test Redis
  redis-cli ping
  
  # Test backend
  curl http://localhost:8000/health
  ```

- [ ] 7.2.4 Fix any issues found

---

## Phase 8: Frontend Integration

### Task 8.1: Fix Frontend Type Issues
**Priority:** Low 🟢  
**Estimated Time:** 2 hours  
**Dependencies:** Phase 3 (API types fixed)  
**Requirements:** User Story 7.1

- [ ] 8.1.1 Run FrontendValidator
  ```bash
  python -m audit.checkers.frontend_validator
  ```

- [ ] 8.1.2 Review identified issues
  - Check type mismatches
  - Check CORS configuration
  - Check error handling

- [ ] 8.1.3 Fix type issues
  - Update TypeScript types to match backend
  - Add missing types
  - Fix type imports

- [ ] 8.1.4 Verify CORS configuration
  ```python
  # In backend/main.py
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

- [ ] 8.1.5 Test frontend-backend integration
  - Start backend
  - Start frontend
  - Test API calls
  - Verify no CORS errors

---

## Phase 9: Final Validation

### Task 9.1: Run Complete Audit
**Priority:** Critical 🔴  
**Estimated Time:** 30 minutes  
**Dependencies:** All previous phases  
**Requirements:** All

- [ ] 9.1.1 Run full audit
  ```bash
  cd fractal_memory
  python -m audit.main --full --output-file audit_reports/audit_final.md
  ```

- [ ] 9.1.2 Compare with initial audit
  - Initial: 57 real issues
  - Final: Should be < 10 issues
  - Document improvements

- [ ] 9.1.3 Verify all critical issues resolved
  - 0 critical issues
  - 0 high priority issues
  - < 5 medium priority issues

---

### Task 9.2: Run E2E Tests
**Priority:** Critical 🔴  
**Estimated Time:** 1 hour  
**Dependencies:** All previous phases  
**Requirements:** All

- [ ] 9.2.1 Test chat flow
  ```bash
  python -c "from audit.testers.e2e_validator import E2EFlowValidator; v = E2EFlowValidator(); v.test_chat_flow()"
  ```

- [ ] 9.2.2 Test memory persistence
  ```bash
  python -c "from audit.testers.e2e_validator import E2EFlowValidator; v = E2EFlowValidator(); v.test_memory_persistence()"
  ```

- [ ] 9.2.3 Test learning flow
  ```bash
  python -c "from audit.testers.e2e_validator import E2EFlowValidator; v = E2EFlowValidator(); v.test_learning_flow()"
  ```

- [ ] 9.2.4 Verify all tests pass
  - All E2E tests should pass
  - Document any remaining issues
  - Create follow-up tasks if needed

---

### Task 9.3: Update Documentation
**Priority:** Medium 🟡  
**Estimated Time:** 2 hours  
**Dependencies:** All previous phases  
**Requirements:** All

- [ ] 9.3.1 Document fixes made
  - Create FIXES.md with summary
  - List all issues resolved
  - Document any breaking changes

- [ ] 9.3.2 Update README if needed
  - Update setup instructions
  - Update architecture docs
  - Add troubleshooting section

- [ ] 9.3.3 Update audit documentation
  - Update audit/README.md with lessons learned
  - Add new common issues to COMMON_ISSUES.md
  - Document audit best practices

- [ ] 9.3.4 Create migration guide if needed
  - Document any API changes
  - Document any schema changes
  - Provide upgrade instructions

---

## Success Checklist

### Phase 1 Complete
- [ ] FractalMemory imports successfully
- [ ] ReasoningBank imports successfully
- [ ] E2EFlowValidator can run
- [ ] RetrievalTester can run

### Phase 2 Complete
- [ ] No Neo4j schema warnings
- [ ] SchemaValidator passes
- [ ] All Strategy queries use correct fields
- [ ] All Episodic queries use correct fields

### Phase 3 Complete
- [ ] Unified types defined
- [ ] All components use unified types
- [ ] APIValidator passes
- [ ] All FastAPI endpoints have response_model

### Phase 4 Complete
- [ ] Vector search works
- [ ] Keyword search works
- [ ] Graph search works
- [ ] L0/L1 search works
- [ ] RRF fusion works
- [ ] RetrievalTester passes all tests

### Phase 5 Complete
- [ ] L0→L1 consolidation works
- [ ] L1→L2 consolidation works
- [ ] promoted_to_l2 flags are set
- [ ] MemoryTester passes all tests

### Phase 6 Complete
- [ ] User isolation verified
- [ ] No cross-user data leaks
- [ ] Property test for user isolation passes

### Phase 7 Complete
- [ ] All required env vars documented
- [ ] Docker Compose works
- [ ] ConfigValidator passes

### Phase 8 Complete
- [ ] Frontend type issues fixed
- [ ] CORS configured correctly
- [ ] FrontendValidator passes

### Phase 9 Complete
- [ ] Full audit shows < 10 issues
- [ ] All E2E tests pass
- [ ] Documentation updated
- [ ] Migration guide created (if needed)

---

## Notes

- Run audit after each phase to catch regressions early
- Test each fix individually before moving to next task
- Keep backups before making schema changes
- Document any unexpected issues discovered
- Update this task list as work progresses
