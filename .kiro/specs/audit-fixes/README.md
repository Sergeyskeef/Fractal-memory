# Audit Fixes Spec

## Quick Start

This spec addresses the 57 real issues found in the Fractal Memory audit (2025-12-06).

### Files in This Spec

1. **requirements.md** - User stories and acceptance criteria organized by epic
2. **tasks.md** - Step-by-step implementation tasks with commands and tests
3. **README.md** - This file

### Priority Overview

**Critical Issues (Must Fix First):**
- Fix FractalMemory module import (blocks all integration tests)
- Fix ReasoningBank module import (blocks learning tests)
- Fix Neo4j Schema field references (23 issues with Strategy.strategy field)

**High Priority Issues:**
- API consistency (SearchResult format, method signatures)
- Search system testing (vector, keyword, graph, L0/L1, RRF)
- User isolation verification

**Medium Priority Issues:**
- Memory consolidation (L0→L1→L2)
- Configuration validation

**Low Priority Issues:**
- Frontend type issues (4 minor issues)
- Environment variable documentation

### Quick Command Reference

```bash
# Run full audit
cd fractal_memory
python -m audit.main --full --output-file audit_reports/audit_latest.md

# Run static analysis only (fast)
python -m audit.main --static-only

# Run runtime tests only
python -m audit.main --runtime-only

# Test specific component
python -c "from audit.checkers.schema_validator import SchemaValidator; v = SchemaValidator(); v.run()"

# Test imports
python -c "from fractal_memory import FractalMemory"
python -c "from reasoning_bank import ReasoningBank"

# Check Neo4j schema
docker exec -it fractal_memory_neo4j cypher-shell -u neo4j -p password "MATCH (s:Strategy) RETURN keys(s) LIMIT 1"
```

### Recommended Workflow

1. **Start with Phase 1** (Critical Imports)
   - Fix `src/__init__.py` to export FractalMemory
   - Fix ReasoningBank import
   - Re-run audit to verify

2. **Move to Phase 2** (Critical Schema)
   - Query Neo4j to find actual Strategy fields
   - Update all code to use correct field names
   - Re-run SchemaValidator

3. **Continue with Phase 3** (API Consistency)
   - Create unified type definitions
   - Update all components to use them
   - Add response_model to FastAPI endpoints

4. **Test Search** (Phase 4)
   - Now that imports work, test all search types
   - Fix any issues found

5. **Verify Memory** (Phase 5)
   - Test consolidation L0→L1→L2
   - Verify promoted_to_l2 flags

6. **Final Validation** (Phase 9)
   - Run full audit
   - Run all E2E tests
   - Update documentation

### Expected Timeline

- **Phase 1 (Critical Imports):** 2-4 hours
- **Phase 2 (Critical Schema):** 1-2 hours
- **Phase 3 (API Consistency):** 4-6 hours
- **Phase 4 (Search Testing):** 4-6 hours
- **Phase 5 (Memory Testing):** 4-6 hours
- **Phase 6 (User Isolation):** 2-3 hours
- **Phase 7 (Configuration):** 2-3 hours
- **Phase 8 (Frontend):** 2-3 hours
- **Phase 9 (Final Validation):** 3-4 hours

**Total:** ~1 week (5-7 working days)

### Success Metrics

**After Phase 1:**
- ✅ `from fractal_memory import FractalMemory` works
- ✅ E2EFlowValidator can run (even if tests fail)

**After Phase 2:**
- ✅ No Neo4j schema warnings in logs
- ✅ SchemaValidator passes

**After All Phases:**
- ✅ Audit shows < 10 total issues (down from 57)
- ✅ All critical and high priority issues resolved
- ✅ All E2E tests pass

### Getting Help

- See `audit/README.md` for audit system documentation
- See `audit/COMMON_ISSUES.md` for examples of fixes
- See `AUDIT_ANALYSIS_RU.md` for detailed issue analysis
- Run audit with `--help` for all options

### Related Documents

- **Audit Report:** `audit_reports/audit_report_20251206_215936.md`
- **Audit Analysis:** `AUDIT_ANALYSIS_RU.md`
- **Audit Summary:** `AUDIT_SUMMARY.md`
- **Audit System Docs:** `audit/README.md`
- **Common Issues:** `audit/COMMON_ISSUES.md`

---

## Next Steps

1. Read `requirements.md` to understand the user stories
2. Read `tasks.md` to see the implementation plan
3. Start with Phase 1, Task 1.1 (Fix FractalMemory import)
4. Run audit after each phase to verify progress
5. Update this spec if you discover new issues

Good luck! 🚀
