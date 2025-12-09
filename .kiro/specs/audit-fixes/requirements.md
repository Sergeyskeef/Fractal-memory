# Spec: Fixing Fractal Memory Audit Issues

## Overview

This spec addresses the 57 real issues found by the comprehensive audit of the Fractal Memory project. The issues are organized by priority and impact, with clear acceptance criteria for each fix.

**Audit Date:** 2025-12-06  
**Total Real Issues:** 57 (excluding 282 node_modules issues)  
**Critical Priority:** 3 issue categories  
**High Priority:** 4 issue categories  
**Medium Priority:** 2 issue categories  

---

## User Stories

### Epic 1: Critical Import and Module Issues

**As a developer**, I need the core FractalMemory module to be importable so that integration tests and E2E flows can run successfully.

**User Story 1.1: Fix FractalMemory Module Import**
- **Priority:** Critical 🔴
- **Affected Tests:** E2EFlowValidator, RetrievalTester, Integration tests
- **Current Issue:** `No module named 'fractal_memory'` prevents all integration testing
- **Acceptance Criteria:**
  - [ ] `from fractal_memory import FractalMemory` works without errors
  - [ ] `src/__init__.py` exports all public classes
  - [ ] Integration tests can import and instantiate FractalMemory
  - [ ] E2E flow tests pass the import phase

**User Story 1.2: Fix ReasoningBank Module Import**
- **Priority:** Critical 🔴
- **Affected Tests:** LearningTester, E2E learning flow
- **Current Issue:** `No module named 'reasoning_bank'` prevents learning system testing
- **Acceptance Criteria:**
  - [ ] `from reasoning_bank import ReasoningBank` works without errors
  - [ ] Learning tests can access strategy creation and retrieval
  - [ ] E2E learning flow completes successfully

---

### Epic 2: Neo4j Schema Consistency

**As a developer**, I need the code to reference actual Neo4j schema fields so that queries execute without warnings and return correct data.

**User Story 2.1: Fix Strategy Node Field References**
- **Priority:** Critical 🔴
- **Affected Components:** Learning system, strategy retrieval
- **Current Issue:** Code references `s.strategy` field that doesn't exist (23 occurrences)
- **Acceptance Criteria:**
  - [ ] Identify actual field names in Strategy nodes (run `MATCH (s:Strategy) RETURN keys(s) LIMIT 1`)
  - [ ] Update all Cypher queries to use correct field names
  - [ ] No Neo4j warnings about missing property keys
  - [ ] SchemaValidator passes all Strategy field checks

**User Story 2.2: Verify Episodic Node Fields**
- **Priority:** High 🟠
- **Affected Components:** Memory system, consolidation
- **Current Issue:** Potential mismatches in fields like `deleted`, `importance_score`, `user_id`
- **Acceptance Criteria:**
  - [ ] Document actual Episodic node schema
  - [ ] Verify all code uses correct field names
  - [ ] Update queries if needed
  - [ ] SchemaValidator passes all Episodic field checks

**User Story 2.3: Verify User Isolation Implementation**
- **Priority:** High 🟠
- **Affected Components:** All memory operations
- **Current Issue:** Need to verify `[user:<id>]` filtering works correctly
- **Acceptance Criteria:**
  - [ ] Test that different users' data is isolated
  - [ ] Verify content field contains user tags
  - [ ] Confirm queries filter by user correctly
  - [ ] Add property test for user isolation (if not exists)

---

### Epic 3: API Consistency and Type Safety

**As a developer**, I need consistent API contracts between components so that data flows correctly through the system.

**User Story 3.1: Standardize SearchResult Format**
- **Priority:** High 🟠
- **Affected Components:** HybridRetriever, FractalMemory, FastAPI endpoints
- **Current Issue:** Different components may use different SearchResult formats
- **Acceptance Criteria:**
  - [ ] Create unified `SearchResult` type in `src/types.py` or similar
  - [ ] Define standard structure: `{content, score, source, metadata}`
  - [ ] Update all components to use the standard type
  - [ ] APIValidator passes SearchResult format checks

**User Story 3.2: Verify FractalMemory API Completeness**
- **Priority:** High 🟠
- **Affected Components:** FractalMemory class
- **Current Issue:** May be missing expected methods
- **Acceptance Criteria:**
  - [ ] Verify presence of: `remember()`, `search()`, `consolidate()`, `get_stats()`
  - [ ] Add missing methods if needed
  - [ ] Document method signatures
  - [ ] APIValidator passes FractalMemory API checks

**User Story 3.3: Verify HybridRetriever API Completeness**
- **Priority:** High 🟠
- **Affected Components:** HybridRetriever class
- **Current Issue:** May be missing expected methods
- **Acceptance Criteria:**
  - [ ] Verify presence of: `search()`, `vector_search()`, `keyword_search()`, `graph_search()`
  - [ ] Add missing methods if needed
  - [ ] Document method signatures
  - [ ] APIValidator passes HybridRetriever API checks

**User Story 3.4: Add Response Models to FastAPI Endpoints**
- **Priority:** Medium 🟡
- **Affected Components:** FastAPI backend
- **Current Issue:** Some endpoints lack `response_model` parameter
- **Acceptance Criteria:**
  - [ ] Identify all endpoints without `response_model`
  - [ ] Create Pydantic models for responses
  - [ ] Add `response_model` to all endpoints
  - [ ] APIValidator passes FastAPI endpoint checks

---

### Epic 4: Memory Consolidation and Lifecycle

**As a user**, I need memory to consolidate properly across levels so that important information persists and unimportant information decays.

**User Story 4.1: Verify L0→L1 Consolidation**
- **Priority:** Medium 🟡
- **Affected Components:** Redis memory store, consolidation logic
- **Current Issue:** No L1 keys found in Redis during audit
- **Acceptance Criteria:**
  - [ ] Verify consolidation triggers are working
  - [ ] Check key format: `memory:{user}:l1:session:{id}`
  - [ ] Confirm importance threshold is correct
  - [ ] MemoryTester passes L0→L1 consolidation test

**User Story 4.2: Verify L1→L2 Consolidation**
- **Priority:** Medium 🟡
- **Affected Components:** Neo4j memory store, consolidation logic
- **Current Issue:** No `promoted_to_l2` flags found in audit
- **Acceptance Criteria:**
  - [ ] Verify L1→L2 promotion logic executes
  - [ ] Check that `promoted_to_l2` flag is set on Episodic nodes
  - [ ] Confirm data moves from Redis to Neo4j
  - [ ] MemoryTester passes L1→L2 consolidation test

**User Story 4.3: Test Complete Memory Lifecycle**
- **Priority:** Medium 🟡
- **Affected Components:** Full memory system
- **Current Issue:** Need end-to-end verification of memory flow
- **Acceptance Criteria:**
  - [ ] Create test memory item
  - [ ] Verify it appears in L0 (Redis)
  - [ ] Trigger consolidation to L1
  - [ ] Trigger consolidation to L2 (Neo4j)
  - [ ] Verify decay logic works
  - [ ] E2EFlowValidator passes memory persistence test

---

### Epic 5: Search and Retrieval System

**As a user**, I need search to work across all memory levels so that I can find relevant information regardless of where it's stored.

**User Story 5.1: Test Vector Search**
- **Priority:** High 🟠
- **Affected Components:** Graphiti integration, vector embeddings
- **Current Issue:** Cannot test due to FractalMemory import issue
- **Acceptance Criteria:**
  - [ ] Fix FractalMemory import (dependency)
  - [ ] Run vector search test with real embeddings
  - [ ] Verify results have similarity scores
  - [ ] RetrievalTester passes vector search test

**User Story 5.2: Test Keyword Search**
- **Priority:** High 🟠
- **Affected Components:** Neo4j fulltext index
- **Current Issue:** Cannot test due to FractalMemory import issue
- **Acceptance Criteria:**
  - [ ] Fix FractalMemory import (dependency)
  - [ ] Run keyword search test
  - [ ] Verify fulltext index is used
  - [ ] RetrievalTester passes keyword search test

**User Story 5.3: Test Graph Search**
- **Priority:** High 🟠
- **Affected Components:** Neo4j graph traversal
- **Current Issue:** Cannot test due to FractalMemory import issue
- **Acceptance Criteria:**
  - [ ] Fix FractalMemory import (dependency)
  - [ ] Run graph search test
  - [ ] Verify relationship traversal works
  - [ ] RetrievalTester passes graph search test

**User Story 5.4: Test L0/L1 Search**
- **Priority:** High 🟠
- **Affected Components:** Redis memory search
- **Current Issue:** Cannot test due to FractalMemory import issue
- **Acceptance Criteria:**
  - [ ] Fix FractalMemory import (dependency)
  - [ ] Run L0/L1 search test
  - [ ] Verify recent memories are found
  - [ ] RetrievalTester passes L0/L1 search test

**User Story 5.5: Test RRF Fusion**
- **Priority:** Medium 🟡
- **Affected Components:** Result merging logic
- **Current Issue:** Cannot test due to FractalMemory import issue
- **Acceptance Criteria:**
  - [ ] Fix FractalMemory import (dependency)
  - [ ] Run RRF fusion test
  - [ ] Verify results from multiple sources are merged correctly
  - [ ] RetrievalTester passes RRF fusion test

---

### Epic 6: Configuration and Environment

**As a developer**, I need proper configuration so that the system can connect to all required services.

**User Story 6.1: Verify Environment Variables**
- **Priority:** Low 🟢
- **Affected Components:** Configuration system
- **Current Issue:** May be missing required environment variables
- **Acceptance Criteria:**
  - [ ] Compare `.env.example` with `.env`
  - [ ] Document all required variables
  - [ ] Add validation for required variables at startup
  - [ ] ConfigValidator passes environment variable checks

**User Story 6.2: Verify Docker Compose Configuration**
- **Priority:** Low 🟢
- **Affected Components:** Docker setup
- **Current Issue:** Potential issues with volumes or ports
- **Acceptance Criteria:**
  - [ ] Review `docker-compose.yml` for correctness
  - [ ] Verify all services start successfully
  - [ ] Check volume mounts and port mappings
  - [ ] ConfigValidator passes Docker Compose checks

---

### Epic 7: Frontend Integration

**As a developer**, I need the frontend to correctly integrate with the backend API.

**User Story 7.1: Fix Frontend Type Issues**
- **Priority:** Low 🟢
- **Affected Components:** React/TypeScript frontend
- **Current Issue:** 4 minor type or configuration issues
- **Acceptance Criteria:**
  - [ ] Review FrontendValidator output
  - [ ] Fix identified type mismatches
  - [ ] Verify CORS configuration
  - [ ] FrontendValidator passes all checks

---

## Success Metrics

### Phase 1 Success (Critical Issues Fixed)
- [ ] All imports work: `from fractal_memory import FractalMemory` succeeds
- [ ] No Neo4j schema warnings in logs
- [ ] SchemaValidator passes with 0 critical issues
- [ ] E2EFlowValidator can run (even if some tests fail)

### Phase 2 Success (High Priority Issues Fixed)
- [ ] APIValidator passes with 0 high priority issues
- [ ] All search types return results
- [ ] RetrievalTester passes all tests
- [ ] User isolation verified

### Phase 3 Success (All Issues Fixed)
- [ ] Full audit passes with 0 critical, 0 high, 0 medium issues
- [ ] Only low priority or informational issues remain
- [ ] All E2E flows complete successfully
- [ ] Memory consolidation works across all levels

### Overall Success
- [ ] Audit report shows < 10 total issues (down from 57)
- [ ] All critical and high priority issues resolved
- [ ] System passes full E2E testing
- [ ] Documentation updated with fixes

---

## Dependencies

### External Dependencies
- Neo4j database must be running
- Redis must be running
- Python environment with all packages installed
- Frontend build tools available

### Internal Dependencies
- Epic 1 (imports) must be fixed before Epic 5 (search) can be tested
- Epic 2 (schema) should be fixed before Epic 4 (consolidation) is fully tested
- Epic 3 (API) should be fixed before Epic 7 (frontend) is fully tested

---

## Out of Scope

The following are explicitly out of scope for this spec:
- Performance optimization (unless it causes functional issues)
- Adding new features
- Refactoring code that works correctly
- Fixing the 282 node_modules issues (these are external dependencies)
- UI/UX improvements
- Adding new tests beyond what's needed to verify fixes

---

## Risk Assessment

### High Risk
- **Schema changes**: Modifying Neo4j queries could break existing functionality
  - **Mitigation**: Test each query change individually, keep backups
  
- **Import structure changes**: Changing `__init__.py` could break existing imports
  - **Mitigation**: Add imports incrementally, test after each change

### Medium Risk
- **API changes**: Modifying API contracts could break frontend
  - **Mitigation**: Ensure backward compatibility, update frontend simultaneously

### Low Risk
- **Configuration changes**: Environment variable changes are low risk
- **Documentation updates**: No functional risk

---

## Timeline Estimate

### Phase 1: Critical Issues (2-4 hours)
- Fix imports: 1-2 hours
- Fix Neo4j schema: 1-2 hours

### Phase 2: High Priority Issues (1-2 days)
- API consistency: 4-6 hours
- Search system testing: 2-4 hours
- User isolation verification: 2-3 hours

### Phase 3: Medium/Low Priority Issues (2-3 days)
- Memory consolidation: 4-6 hours
- Configuration: 2-3 hours
- Frontend fixes: 2-3 hours
- Documentation: 2-3 hours

**Total Estimated Time:** 1 week (5-7 working days)

---

## Notes

- This spec is based on the audit report generated on 2025-12-06
- Issues are prioritized by impact on system functionality
- Some issues may be resolved as side effects of fixing other issues
- Re-run the audit after each epic to verify fixes and catch regressions
- Update this spec if new issues are discovered during implementation
