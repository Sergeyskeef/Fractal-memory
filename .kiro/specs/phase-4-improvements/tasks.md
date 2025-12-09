# Implementation Plan: Phase 4 Improvements

## Overview
This implementation plan addresses remaining non-critical issues in the Fractal Memory project by improving memory validation, schema recognition, and audit filtering.

## Tasks

- [x] 1. Improve MemoryTester L1 validation logic
  - Update `test_l0_to_l1_consolidation()` to handle optional fields gracefully
  - Make importance and summary truly optional
  - Improve error messages to be more descriptive
  - Distinguish between critical and informational issues
  - _Requirements: 1.1, 1.2, 1.4_

- [x] 1.1 Write property test for memory data consistency
  - **Property 1: Memory Data Consistency Across Tiers**
  - **Validates: Requirements 1.2**
  - Generate random memory operations and verify data consistency across tiers

- [x] 1.2 Write property test for consolidation integrity
  - **Property 2: Memory Consolidation Integrity**
  - **Validates: Requirements 1.4**
  - Generate random consolidation operations and verify integrity constraints

- [x] 1.3 Write property test for retrieval consistency
  - **Property 3: Memory Retrieval Consistency**
  - **Validates: Requirements 1.5**
  - Store data in different tiers and verify retrieval consistency

- [x] 2. Add Graphiti pattern recognition to SchemaValidator
  - Define `GRAPHITI_INDEXES`, `GRAPHITI_NODE_LABELS`, `GRAPHITI_RELATIONSHIPS` constants
  - Implement `is_graphiti_managed()` method
  - Update `check_indexes()` to recognize Graphiti patterns
  - Update `check_node_labels()` to recognize Graphiti labels
  - Update `check_relationships()` to recognize Graphiti relationships
  - _Requirements: 2.1, 2.2, 2.4_

- [x] 2.1 Write property test for schema categorization
  - **Property 4: Schema Categorization Accuracy**
  - **Validates: Requirements 2.1**
  - Test that critical vs acceptable differences are correctly categorized

- [x] 2.2 Write property test for Graphiti element recognition
  - **Property 5: Graphiti Element Recognition**
  - **Validates: Requirements 2.2, 2.4**
  - Test all known Graphiti elements are recognized as valid

- [x] 3. Add node_modules filtering to ImportChecker
  - Implement `should_skip_file()` method with exclusion patterns
  - Add configuration for exclusion patterns in `AuditConfig`
  - Update `_check()` to filter files before checking
  - Update report generation to show filtered vs total counts
  - _Requirements: 4.3_

- [x] 3.1 Write property test for node_modules exclusion
  - **Property 11: Node Modules Exclusion**
  - **Validates: Requirements 4.3**
  - Generate issues from various paths and verify node_modules are excluded

- [ ] 4. Improve configuration validation
  - Add validation for all required config parameters in `AuditConfig.__init__()`
  - Improve error messages for missing/invalid config values
  - Add sensible defaults for optional parameters
  - Document configuration precedence rules
  - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [ ] 4.1 Write property test for configuration validation
  - **Property 6: Configuration Validation Completeness**
  - **Validates: Requirements 3.1**
  - Test that all required parameters are validated at startup

- [ ] 4.2 Write property test for configuration error messages
  - **Property 7: Configuration Error Clarity**
  - **Validates: Requirements 3.2**
  - Generate invalid configs and verify error message clarity

- [ ] 4.3 Write property test for configuration defaults
  - **Property 8: Configuration Default Behavior**
  - **Validates: Requirements 3.3**
  - Test each optional parameter returns correct default when unset

- [ ] 4.4 Write property test for configuration merge
  - **Property 9: Configuration Merge Precedence**
  - **Validates: Requirements 3.5**
  - Test various configuration combinations follow precedence rules

- [ ] 5. Improve audit issue categorization
  - Create `IssueFilter` class for filtering logic
  - Update `ReportGenerator` to use `IssueFilter`
  - Add severity categorization validation
  - Ensure consistent issue categorization across all checkers
  - _Requirements: 4.2_

- [ ] 5.1 Write property test for issue categorization
  - **Property 10: Issue Severity Categorization**
  - **Validates: Requirements 4.2**
  - Generate various issues and verify correct severity assignment

- [ ] 5.2 Write property test for audit determinism
  - **Property 12: Audit Determinism**
  - **Validates: Requirements 4.5**
  - Run audit multiple times and verify consistent results

- [ ] 6. Update documentation
  - Document acceptable schema differences in `docs/` or `audit/README.md`
  - Update audit configuration documentation
  - Add examples of Graphiti-managed schema elements
  - Document exclusion patterns for ImportChecker
  - _Requirements: 2.5_

- [ ] 7. Checkpoint - Verify all improvements
  - Run full audit and verify issue counts are reduced
  - MemoryTester should report 0 issues (down from 2)
  - SchemaValidator should report ≤10 issues (down from 21)
  - ImportChecker should exclude node_modules from main count
  - All property tests should pass with 100+ iterations
  - Ensure all tests pass, ask the user if questions arise

## Notes

- All tasks are required for comprehensive implementation
- Property tests should run 100+ iterations each
- Each property test must be tagged with the format: `# Feature: phase-4-improvements, Property {number}: {property_text}`
- Focus on reducing false positives while maintaining detection of real issues
- Tests should be written after implementation to validate the improvements
