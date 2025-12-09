# Remaining Critical Fixes - Requirements

**Created:** 2025-12-07  
**Status:** Draft  
**Priority:** 🔴 Critical

## Overview

This specification addresses the remaining critical issues that could block normal project operation and remain unresolved after Phases 0-3.

## Problem Statement

After completing Phases 0-3, the audit shows:
- **Total Issues:** 334
- **Critical:** 0
- **High:** 304 (mostly node_modules imports - can ignore)
- **Medium:** 26
- **Low:** 4

**Real Critical Issues:**
1. **FractalMemory.remember() API mismatch** - Tests call with `user_id` parameter, but method doesn't accept it (13 test failures)
2. **Config issues** - 2 configuration problems
3. **Schema issues** - 21 Neo4j schema validation issues
4. **Frontend issues** - 12 CORS and type issues

## Requirements

### REQ-1: Fix FractalMemory.remember() API

**Priority:** 🔴 Critical  
**Category:** memory

**Problem:**
Tests are calling `memory.remember(content=..., importance=..., user_id=...)` but the method signature is:
```python
async def remember(self, content: str, importance: float = 1.0, metadata: Dict = None) -> str
```

The `user_id` is already set in FractalMemory constructor via config, so tests shouldn't pass it.

**Acceptance Criteria:**

1. **AC-1.1:** WHEN tests call `remember()` without `user_id` parameter, THEN the method SHALL use the `user_id` from config
2. **AC-1.2:** WHEN tests call `remember()` with `user_id` in metadata dict, THEN the method SHALL accept it
3. **AC-1.3:** WHEN `remember()` is called, THEN it SHALL NOT accept `user_id` as a direct parameter
4. **AC-1.4:** WHEN all memory tests run, THEN they SHALL pass without `user_id` parameter errors
5. **AC-1.5:** WHEN all retrieval tests run, THEN they SHALL pass without `user_id` parameter errors
6. **AC-1.6:** WHEN all E2E tests run, THEN they SHALL pass without `user_id` parameter errors

**Impact:** 13 test failures (5 memory + 5 retrieval + 3 integration)

### REQ-2: Fix Test Files to Remove user_id Parameter

**Priority:** 🔴 Critical  
**Category:** testing

**Problem:**
Multiple test files are incorrectly passing `user_id` as a direct parameter to `remember()`.

**Files to Fix:**
- `audit/testers/memory_tester.py` (3 calls)
- `audit/testers/retrieval_tester.py` (1 call)
- `audit/testers/e2e_validator.py` (2 calls)

**Acceptance Criteria:**

1. **AC-2.1:** WHEN memory_tester calls `remember()`, THEN it SHALL NOT pass `user_id` as parameter
2. **AC-2.2:** WHEN retrieval_tester calls `remember()`, THEN it SHALL NOT pass `user_id` as parameter
3. **AC-2.3:** WHEN e2e_validator calls `remember()`, THEN it SHALL NOT pass `user_id` as parameter
4. **AC-2.4:** WHEN tests need user isolation, THEN they SHALL create separate FractalMemory instances with different user_ids in config
5. **AC-2.5:** WHEN all tests run, THEN they SHALL pass without TypeError

**Impact:** Fixes 13 test failures

### REQ-3: Fix Configuration Issues

**Priority:** 🟠 High  
**Category:** config

**Problem:**
ConfigValidator reports 2 configuration issues.

**Acceptance Criteria:**

1. **AC-3.1:** WHEN ConfigValidator runs, THEN it SHALL report 0 issues
2. **AC-3.2:** WHEN environment variables are checked, THEN all required variables SHALL be documented
3. **AC-3.3:** WHEN Docker Compose config is checked, THEN it SHALL be valid
4. **AC-3.4:** WHEN backend configuration is checked, THEN it SHALL be consistent

**Impact:** Configuration consistency

### REQ-4: Address Schema Validation Issues

**Priority:** 🟡 Medium  
**Category:** schema

**Problem:**
SchemaValidator reports 21 Neo4j schema issues.

**Acceptance Criteria:**

1. **AC-4.1:** WHEN SchemaValidator runs, THEN it SHALL report ≤ 10 issues (reduce by 50%)
2. **AC-4.2:** WHEN Cypher queries are validated, THEN they SHALL use correct node labels
3. **AC-4.3:** WHEN relationships are checked, THEN they SHALL match the schema
4. **AC-4.4:** WHEN indexes are checked, THEN they SHALL exist in the database

**Impact:** Schema consistency and query reliability

### REQ-5: Fix Frontend Issues

**Priority:** 🟡 Medium  
**Category:** frontend

**Problem:**
FrontendValidator reports 12 issues (CORS, types, error handling).

**Acceptance Criteria:**

1. **AC-5.1:** WHEN CORS is configured, THEN it SHALL allow frontend origin
2. **AC-5.2:** WHEN API types are checked, THEN they SHALL match backend models
3. **AC-5.3:** WHEN error handling is checked, THEN it SHALL be consistent
4. **AC-5.4:** WHEN FrontendValidator runs, THEN it SHALL report ≤ 5 issues (reduce by 60%)

**Impact:** Frontend-backend integration

## Non-Requirements

1. **Fixing node_modules imports** - 282 issues in vitest/vite node_modules can be ignored
2. **Learning issues** - 4 issues in LearningTester are low priority (tests pass)
3. **Complete schema perfection** - Some schema issues may be acceptable

## Success Criteria

After implementing all requirements:

1. **Test Results:**
   - MemoryTester: ✅ PASSED (0 issues)
   - RetrievalTester: ✅ PASSED (0 issues)
   - E2EFlowValidator: ✅ PASSED (0 issues)
   - ConfigValidator: ✅ PASSED (0 issues)

2. **Issue Reduction:**
   - Memory issues: 5 → 0 (100% reduction)
   - Retrieval issues: 5 → 0 (100% reduction)
   - Integration issues: 3 → 0 (100% reduction)
   - Config issues: 2 → 0 (100% reduction)
   - Schema issues: 21 → ≤10 (50% reduction)
   - Frontend issues: 12 → ≤5 (60% reduction)

3. **Total Issues:**
   - Before: 334
   - After: ≤300 (10% reduction in real issues)

## Glossary

- **FractalMemory** - Main memory class with hierarchical levels (L0-L3)
- **user_id** - User identifier for memory isolation
- **remember()** - Method to store information in memory
- **ConfigValidator** - Audit checker for configuration consistency
- **SchemaValidator** - Audit checker for Neo4j schema validation

## References

- Phase 0 Report: `CRITICAL_FIXES_COMPLETE.md`
- Phase 3 Report: `PHASE3_API_CONSISTENCY_COMPLETE.md`
- Latest Audit: `audit_reports/audit_report_20251207_034005.md`
