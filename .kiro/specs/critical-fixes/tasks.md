# Implementation Plan: Critical Bug Fixes

## Overview
This plan outlines the implementation tasks for fixing critical bugs in the Fractal Memory project, focusing on FractalAgent initialization, configuration consistency, and error handling improvements.

## Tasks

- [x] 1. Fix FractalAgent initialization to support external components
  - Update `FractalAgent.__init__()` to accept `memory`, `retriever`, and `reasoning` parameters
  - Add component ownership tracking (`_owns_memory`, `_owns_retriever`, `_owns_reasoning`)
  - Update `initialize()` method to use provided components or create new ones
  - Update `close()` method to only close owned components
  - Add deprecation warnings for future API changes
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 3.1, 3.2, 3.3, 3.5_

- [x] 1.1 Write property test for FractalAgent initialization with provided memory
  - **Property 4: Provided memory instance is used**
  - **Validates: Requirements 1.4**

- [x] 1.2 Write property test for successful initialization state
  - **Property 1: Successful initialization sets correct state**
  - **Validates: Requirements 1.5**

- [x] 1.3 Write property test for all components initialized
  - **Property 2: All components initialized after successful init**
  - **Validates: Requirements 1.2**

- [x] 1.4 Write property test for GraphitiStore sharing
  - **Property 8: GraphitiStore instance is shared**
  - **Validates: Requirements 3.2, 3.3, 3.4**

- [x] 1.5 Write property test for cleanup of owned components
  - **Property 9: Close cleans up owned components**
  - **Validates: Requirements 3.5**

- [ ] 2. Enhance error handling and logging
  - Add `_identify_failed_component()` method to identify which component failed
  - Update `initialize()` to provide detailed error messages with component names
  - Add `ComponentError` exception class with component name and details
  - Implement password sanitization in log messages
  - Update all error logging to include component context
  - _Requirements: 1.3, 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 2.1 Write property test for error messages containing component names
  - **Property 3: Error messages contain component names**
  - **Validates: Requirements 1.3, 4.1**

- [ ] 2.2 Write property test for ERROR state on failed initialization
  - **Property 10: Failed initialization sets ERROR state**
  - **Validates: Requirements 4.5**

- [ ] 2.3 Write property test for password sanitization in logs
  - **Property 11: Logs contain connection details without passwords**
  - **Validates: Requirements 4.3**

- [ ] 3. Create unified configuration system
  - Create `UnifiedConfig` dataclass with all configuration parameters
  - Implement `from_dict()` class method with parameter name mapping
  - Implement `to_dict()` method for backward compatibility
  - Add parameter mapping dictionary for old parameter names
  - Update FractalAgent to use UnifiedConfig internally
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 3.1 Write property test for config merge preserving values
  - **Property 5: Config merge preserves provided values**
  - **Validates: Requirements 2.3**

- [ ] 3.2 Write property test for missing required params handling
  - **Property 6: Missing required params handled correctly**
  - **Validates: Requirements 2.4**

- [ ] 3.3 Write property test for environment variable precedence
  - **Property 7: Environment variables take precedence**
  - **Validates: Requirements 2.5**

- [ ] 3.4 Write property test for old parameter name mapping
  - **Property 16: Old parameter names are mapped**
  - **Validates: Requirements 6.2**

- [ ] 4. Update E2EFlowValidator to use new initialization pattern
  - Update E2EFlowValidator to pass memory via parameter instead of config
  - Ensure proper cleanup in teardown
  - Add test data isolation with unique user_ids
  - Verify all tests pass with new initialization
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 4.1 Write property test for test data isolation
  - **Property 12: Test data isolation**
  - **Validates: Requirements 5.2**

- [ ] 4.2 Write property test for test cleanup
  - **Property 13: Test cleanup releases resources**
  - **Validates: Requirements 5.3**

- [ ] 4.3 Write property test for parallel test isolation
  - **Property 14: Parallel tests don't conflict**
  - **Validates: Requirements 5.5**

- [ ] 5. Add backward compatibility support
  - Implement deprecation warning system
  - Add warnings for old initialization patterns
  - Create migration guide documentation
  - Update all internal code to use new patterns
  - _Requirements: 6.1, 6.2, 6.5_

- [ ] 5.1 Write property test for deprecation warnings
  - **Property 15: Deprecated patterns emit warnings**
  - **Validates: Requirements 6.1, 6.5**

- [ ] 6. Update configuration files for consistency
  - Ensure backend/config.py and audit/config.py use same parameter names
  - Update all config files to use unified parameter names
  - Add validation for required parameters
  - Document all configuration parameters
  - _Requirements: 2.1, 2.2_

- [ ] 7. Checkpoint - Ensure all tests pass
  - Run all unit tests and verify they pass
  - Run all property-based tests and verify they pass
  - Run E2E tests and verify they pass
  - Run audit system and verify critical issues are resolved
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Update documentation
  - Update README with new initialization patterns
  - Add migration guide for old code
  - Document all configuration parameters
  - Add examples of new initialization patterns
  - Document error handling improvements
  - _Requirements: 6.3, 6.4_

## Notes

### Property-Based Testing
- All property tests use `hypothesis` library
- Each test runs minimum 100 iterations
- Each test is tagged with format: `# Feature: critical-fixes, Property N: <description>`
- All tests are required for comprehensive validation

### Testing Strategy
- Unit tests verify specific behaviors and edge cases
- Property tests verify universal properties across many inputs
- Integration tests verify component interactions
- E2E tests verify complete system flows

### Implementation Order
1. Start with FractalAgent initialization fix (Task 1) - this is the critical blocker
2. Add error handling improvements (Task 2) - helps with debugging
3. Create unified config (Task 3) - foundation for consistency
4. Update E2E tests (Task 4) - verify fixes work
5. Add backward compatibility (Task 5) - maintain existing code
6. Update configs (Task 6) - ensure consistency
7. Checkpoint (Task 7) - verify everything works
8. Documentation (Task 8) - help users migrate

### Success Criteria
- ✅ E2E tests pass without initialization errors
- ✅ All property-based tests pass (100+ iterations each)
- ✅ Error messages clearly indicate failed components
- ✅ Configuration is consistent across all components
- ✅ Backward compatibility maintained with deprecation warnings
- ✅ All resources properly cleaned up after use
- ✅ Audit system shows reduced critical issues
