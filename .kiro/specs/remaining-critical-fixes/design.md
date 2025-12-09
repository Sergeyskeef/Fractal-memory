# Remaining Critical Fixes - Design

**Created:** 2025-12-07  
**Status:** Draft

## Architecture Overview

This design addresses the remaining critical issues by:
1. Fixing test files to match FractalMemory API
2. Investigating and fixing configuration issues
3. Reducing schema validation issues
4. Addressing frontend integration issues

## Component Design

### 1. FractalMemory API (No Changes Needed)

The current API is correct:

```python
class FractalMemory:
    def __init__(self, config: Dict):
        self.user_id = config.get("user_id", "default")
        # ...
    
    async def remember(
        self, 
        content: str,
        importance: float = 1.0,
        metadata: Dict = None
    ) -> str:
        # user_id is already available as self.user_id
        # ...
```

**Design Decision:** The `user_id` is set at initialization time, not per-call. This is correct because:
- Each FractalMemory instance is tied to one user
- Tests that need different users should create different instances
- Cleaner API (fewer parameters)

### 2. Test File Fixes

#### 2.1 memory_tester.py

**Current (Incorrect):**
```python
item_id = await self.memory.remember(
    content=test_content,
    importance=initial_importance,
    user_id="test_user_decay"  # ❌ Wrong!
)
```

**Fixed:**
```python
item_id = await self.memory.remember(
    content=test_content,
    importance=initial_importance
    # user_id is already set in self.memory.user_id
)
```

**Locations to Fix:**
1. Line ~430: `test_decay_logic()`
2. Line ~512: `test_garbage_collection()`
3. Line ~604: `test_deduplication()`

#### 2.2 retrieval_tester.py

**Current (Incorrect):**
```python
await self.memory.remember(
    content=f"Test document {i}: {content}",
    importance=0.8,
    user_id="test_user_retrieval"  # ❌ Wrong!
)
```

**Fixed:**
```python
await self.memory.remember(
    content=f"Test document {i}: {content}",
    importance=0.8
)
```

**Locations to Fix:**
1. Line ~160: `test_vector_search()`

#### 2.3 e2e_validator.py

**Current (Incorrect):**
```python
message_id = await self.memory.remember(
    content=message_content,
    importance=0.9,
    user_id=test_user  # ❌ Wrong!
)
```

**Fixed:**
```python
message_id = await self.memory.remember(
    content=message_content,
    importance=0.9
)
```

**Locations to Fix:**
1. Line ~183: `test_chat_flow()`
2. Line ~373: `test_memory_persistence()`

### 3. Configuration Issues Investigation

Need to check what ConfigValidator is reporting:

**Approach:**
1. Run ConfigValidator with verbose output
2. Identify the 2 specific issues
3. Fix based on findings

**Potential Issues:**
- Missing environment variables in `.env.example`
- Docker Compose configuration inconsistencies
- Backend configuration mismatches

**Design Pattern:**
- All config should be documented in `.env.example`
- Docker Compose should reference environment variables
- Backend should validate required config on startup

### 4. Schema Validation Issues

**Current Issues:** 21 schema problems

**Investigation Approach:**
1. Run SchemaValidator with verbose output
2. Categorize issues:
   - Missing indexes
   - Wrong node labels
   - Wrong relationship types
   - Query syntax errors

**Design Strategy:**
- Fix critical schema mismatches (wrong labels/relationships)
- Document acceptable differences (Graphiti vs custom schema)
- Add missing indexes if needed
- Update queries to match actual schema

**Expected Outcome:**
- Reduce from 21 to ≤10 issues
- Document remaining issues as "acceptable differences"

### 5. Frontend Issues

**Current Issues:** 12 frontend problems

**Investigation Approach:**
1. Run FrontendValidator with verbose output
2. Categorize issues:
   - CORS configuration
   - Type mismatches
   - Error handling
   - API endpoint usage

**Design Solutions:**

#### 5.1 CORS Configuration
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "http://localhost:5173",  # Vite dev server
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 5.2 Type Consistency
- Ensure frontend types match `backend/models.py`
- Generate TypeScript types from Pydantic models (optional)

#### 5.3 Error Handling
- Consistent error response format
- Proper HTTP status codes
- Error messages in responses

## Implementation Strategy

### Phase 1: Fix Test Files (30 minutes)
**Priority:** 🔴 Critical

1. Fix `memory_tester.py` (3 locations)
2. Fix `retrieval_tester.py` (1 location)
3. Fix `e2e_validator.py` (2 locations)
4. Run tests to verify fixes

**Expected Result:**
- MemoryTester: ✅ PASSED
- RetrievalTester: ✅ PASSED
- E2EFlowValidator: ✅ PASSED

### Phase 2: Fix Configuration (30 minutes)
**Priority:** 🟠 High

1. Run ConfigValidator with verbose output
2. Identify 2 specific issues
3. Fix issues
4. Verify with ConfigValidator

**Expected Result:**
- ConfigValidator: ✅ PASSED

### Phase 3: Reduce Schema Issues (1 hour)
**Priority:** 🟡 Medium

1. Run SchemaValidator with verbose output
2. Categorize 21 issues
3. Fix critical issues (wrong labels/relationships)
4. Document acceptable differences
5. Verify reduction to ≤10 issues

**Expected Result:**
- SchemaValidator: Still ❌ FAILED but with ≤10 issues

### Phase 4: Fix Frontend Issues (1 hour)
**Priority:** 🟡 Medium

1. Run FrontendValidator with verbose output
2. Fix CORS configuration
3. Fix type mismatches
4. Fix error handling
5. Verify reduction to ≤5 issues

**Expected Result:**
- FrontendValidator: ✅ PASSED or ≤5 issues

## Testing Strategy

### Unit Tests
- No new unit tests needed (fixing existing tests)

### Integration Tests
- Run full audit after each phase
- Verify issue counts decrease

### Validation
- All test files should run without TypeError
- ConfigValidator should pass
- Schema issues should be reduced by 50%
- Frontend issues should be reduced by 60%

## Rollback Plan

If fixes cause regressions:
1. Git revert to previous commit
2. Analyze what went wrong
3. Fix incrementally with smaller changes

## Success Metrics

| Metric | Before | Target | Success Criteria |
|--------|--------|--------|------------------|
| Memory issues | 5 | 0 | 100% reduction |
| Retrieval issues | 5 | 0 | 100% reduction |
| Integration issues | 3 | 0 | 100% reduction |
| Config issues | 2 | 0 | 100% reduction |
| Schema issues | 21 | ≤10 | 50% reduction |
| Frontend issues | 12 | ≤5 | 60% reduction |
| **Total real issues** | **48** | **≤15** | **70% reduction** |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing tests | Low | High | Run tests after each change |
| Config changes break deployment | Low | High | Test with Docker Compose |
| Schema changes break queries | Medium | Medium | Test queries after changes |
| Frontend changes break UI | Low | Medium | Test frontend after changes |

## Timeline

- **Phase 1:** 30 minutes (Fix test files)
- **Phase 2:** 30 minutes (Fix config)
- **Phase 3:** 1 hour (Reduce schema issues)
- **Phase 4:** 1 hour (Fix frontend)
- **Total:** ~3 hours

## Dependencies

- Docker containers must be running (Neo4j, Redis)
- Environment variables must be set
- Frontend must be available for testing

## Notes

- The 282 import issues in node_modules can be ignored (vitest/vite internals)
- Focus on fixing real issues that affect project functionality
- Document any issues that are "acceptable" and don't need fixing
