# Remaining Critical Fixes - Specification Ready

**Created:** 2025-12-07  
**Status:** ✅ READY TO EXECUTE

## Overview

Complete specification created for fixing remaining critical issues that could block normal project operation.

## Problem Summary

After Phases 0-3, audit shows:
- **Total Issues:** 334
- **Real Critical Issues:** 48 (excluding 282 node_modules imports)

**Breakdown:**
- Memory issues: 5 (FractalMemory.remember() API mismatch)
- Retrieval issues: 5 (same API mismatch)
- Integration issues: 3 (same API mismatch)
- Config issues: 2 (configuration problems)
- Schema issues: 21 (Neo4j schema validation)
- Frontend issues: 12 (CORS, types, error handling)

## Root Cause

**Primary Issue:** Tests are calling `memory.remember(content=..., user_id=...)` but the method doesn't accept `user_id` as a parameter. The `user_id` is set in the FractalMemory constructor via config.

**Impact:** 13 test failures across 3 test files

## Solution Approach

### Phase 1: Fix Test Files (30 min) - 🔴 CRITICAL
Fix 6 `remember()` calls in 3 test files to remove `user_id` parameter.

**Expected Result:**
- MemoryTester: ✅ PASSED
- RetrievalTester: ✅ PASSED  
- E2EFlowValidator: ✅ PASSED
- 13 issues resolved

### Phase 2: Fix Configuration (30 min) - 🟠 HIGH
Investigate and fix 2 configuration issues.

**Expected Result:**
- ConfigValidator: ✅ PASSED
- 2 issues resolved

### Phase 3: Reduce Schema Issues (1 hour) - 🟡 MEDIUM
Categorize and fix critical schema issues.

**Expected Result:**
- Schema issues: 21 → ≤10 (50% reduction)
- 11 issues resolved

### Phase 4: Fix Frontend (1 hour) - 🟡 MEDIUM
Fix CORS, types, and error handling.

**Expected Result:**
- Frontend issues: 12 → ≤5 (60% reduction)
- 7 issues resolved

## Documents Created

1. ✅ **requirements.md** - 5 requirements with 20 acceptance criteria
2. ✅ **design.md** - Detailed design with implementation strategy
3. ✅ **tasks.md** - 12 tasks with step-by-step instructions

## Success Metrics

| Metric | Before | Target | Reduction |
|--------|--------|--------|-----------|
| Memory issues | 5 | 0 | 100% |
| Retrieval issues | 5 | 0 | 100% |
| Integration issues | 3 | 0 | 100% |
| Config issues | 2 | 0 | 100% |
| Schema issues | 21 | ≤10 | 50% |
| Frontend issues | 12 | ≤5 | 60% |
| **Total real issues** | **48** | **≤15** | **70%** |

## Timeline

- **Phase 1:** 30 minutes (Critical test fixes)
- **Phase 2:** 30 minutes (Config fixes)
- **Phase 3:** 1 hour (Schema reduction)
- **Phase 4:** 1 hour (Frontend fixes)
- **Total:** ~3.5 hours

## Next Steps

### Option 1: Execute Immediately
Start with Task 1 (Fix memory_tester.py) - highest impact, lowest risk.

### Option 2: Review First
Review the specification documents and provide feedback.

### Option 3: Prioritize Differently
Choose which phase to tackle first based on your priorities.

## Recommendation

**Start with Phase 1 (Tasks 1-4)** because:
- ✅ Highest impact (fixes 13 test failures)
- ✅ Lowest risk (simple parameter removal)
- ✅ Fastest (30 minutes)
- ✅ Unblocks other work

After Phase 1, you'll have:
- All memory/retrieval/integration tests passing
- Clear path forward for remaining issues
- Confidence that the core functionality works

## Files to Modify

### Phase 1 (Critical):
- `audit/testers/memory_tester.py` (3 changes)
- `audit/testers/retrieval_tester.py` (1 change)
- `audit/testers/e2e_validator.py` (2 changes)

### Phase 2-4 (TBD):
- Will be determined during investigation tasks

## How to Start

### Via Kiro:
```
"Let's start with Phase 1 - fix the test files"
```

### Manually:
1. Open `tasks.md`
2. Follow Task 1 instructions
3. Continue through Task 4

## Questions?

- **Q: Why not fix FractalMemory.remember() to accept user_id?**
  - A: The current design is correct - user_id is set at initialization. Tests are using the API incorrectly.

- **Q: Can we skip Phase 3-4?**
  - A: Yes, Phase 1-2 are critical. Phase 3-4 are improvements but not blockers.

- **Q: What about the 282 import issues?**
  - A: Those are in node_modules (vitest/vite internals) and can be ignored.

---

**Status:** ✅ READY TO EXECUTE  
**Recommendation:** Start with Phase 1 (Tasks 1-4)  
**Estimated Time:** 30 minutes for critical fixes  
**Impact:** Fixes 13 test failures (27% of real issues)
