# Design Document: Phase 4 Improvements

## Overview

This design addresses remaining non-critical issues in the Fractal Memory project after successful resolution of all critical blockers. The focus is on:

1. **Memory Operations** - Fixing 2 issues related to L0/L1 memory structure and validation
2. **Schema Validation** - Reducing 21 schema issues by improving validator logic to recognize Graphiti-managed schemas
3. **Audit System** - Improving issue categorization and filtering to exclude node_modules issues

The improvements will enhance code quality, reduce false positives in audits, and ensure consistency across the memory system.

## Architecture

### Current State

```
Audit System
├── StaticCheckers
│   ├── ImportChecker (282 issues - mostly node_modules)
│   └── SchemaValidator (21 issues - Graphiti schema differences)
└── RuntimeTesters
    ├── MemoryTester (2 issues - L1 structure validation)
    ├── RetrievalTester (4 issues - non-critical)
    └── LearningTester (4 issues - non-critical)
```

### Target State

```
Audit System (Improved)
├── StaticCheckers
│   ├── ImportChecker (filters node_modules)
│   └── SchemaValidator (recognizes Graphiti patterns)
└── RuntimeTesters
    ├── MemoryTester (validates L1 structure correctly)
    ├── RetrievalTester (unchanged)
    └── LearningTester (unchanged)
```

## Components and Interfaces

### 1. MemoryTester Improvements

**Current Issues:**
- L1 keys may be missing expected fields
- Importance validation may fail on edge cases

**Improvements:**
```python
class MemoryTester(RuntimeTester):
    async def test_l0_to_l1_consolidation(self) -> TestResult:
        """
        Improved validation:
        - Handle optional fields gracefully
        - Better error messages
        - Distinguish between critical and informational issues
        """
        
    async def validate_l1_structure(self, key: str, data: dict) -> List[Issue]:
        """
        New method to validate L1 structure with proper field handling.
        
        Required fields: session_id, created_at
        Optional fields: summary, importance, source_count
        """
```

### 2. SchemaValidator Improvements

**Current Issues:**
- Reports Graphiti-managed indexes as issues
- Doesn't distinguish between critical schema mismatches and acceptable differences

**Improvements:**
```python
class SchemaValidator(StaticChecker):
    # Known Graphiti-managed patterns
    GRAPHITI_INDEXES = {
        'entity_uuid', 'episode_uuid', 'relation_uuid',
        'entity_group_id', 'episode_group_id', 'relation_group_id',
        'name_entity_index', 'name_edge_index',
        'created_at_entity_index', 'created_at_episodic_index',
        'valid_at_episodic_index', 'invalid_at_edge_index',
        'episode_content', 'node_name_and_summary', 'edge_name_and_fact',
        'community_uuid', 'community_group_id', 'community_name',
        'mention_uuid', 'mention_group_id', 'has_member_uuid',
    }
    
    GRAPHITI_NODE_LABELS = {'Entity', 'Episodic', 'Community'}
    GRAPHITI_RELATIONSHIPS = {'RELATES_TO', 'MENTIONS', 'HAS_MEMBER'}
    
    async def check_indexes(self, schema: Neo4jSchema) -> List[Issue]:
        """
        Improved index checking:
        - Recognize Graphiti-managed indexes
        - Only report truly missing indexes
        - Reduce false positives
        """
        
    async def is_graphiti_managed(self, index_name: str) -> bool:
        """Check if index is managed by Graphiti."""
```

### 3. ImportChecker Improvements

**Current Issues:**
- Reports 282 issues, mostly in node_modules
- Clutters audit reports with irrelevant issues

**Improvements:**
```python
class ImportChecker(StaticChecker):
    def should_skip_file(self, file_path: Path) -> bool:
        """
        Skip files that shouldn't be checked:
        - node_modules/**
        - .venv/**
        - dist/**
        - build/**
        """
        
    async def _check(self) -> List[Issue]:
        """
        Improved checking:
        - Filter out node_modules by default
        - Add configuration option to include/exclude paths
        - Focus on project code only
        """
```

## Data Models

### Issue Categorization

```python
class IssueFilter:
    """Filter issues based on configuration."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.exclude_patterns = [
            '**/node_modules/**',
            '**/.venv/**',
            '**/dist/**',
            '**/build/**',
        ]
    
    def should_include(self, issue: Issue) -> bool:
        """Determine if issue should be included in report."""
        # Check if issue location matches exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(issue.location, pattern):
                return False
        return True
```

### Schema Validation Model

```python
@dataclass
class SchemaValidationResult:
    """Result of schema validation."""
    
    total_indexes: int
    graphiti_managed: int
    missing_indexes: List[str]
    unexpected_indexes: List[str]
    critical_issues: List[Issue]
    informational_issues: List[Issue]
    
    @property
    def is_valid(self) -> bool:
        """Schema is valid if no critical issues."""
        return len(self.critical_issues) == 0
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Memory Data Consistency Across Tiers
*For any* memory operation (store, retrieve, consolidate), the data should remain consistent across L0, L1, and L2 tiers, with all required fields preserved.

**Validates: Requirements 1.2**

### Property 2: Memory Consolidation Integrity
*For any* memory consolidation operation (L0→L1 or L1→L2), all required data integrity constraints should be preserved, including field presence and value validity.

**Validates: Requirements 1.4**

### Property 3: Memory Retrieval Consistency
*For any* piece of data stored in the memory system, retrieval should return consistent results regardless of which tier (L0, L1, or L2) contains the data.

**Validates: Requirements 1.5**

### Property 4: Schema Categorization Accuracy
*For any* schema validation run, the system should correctly distinguish between critical schema issues and acceptable differences (such as Graphiti-managed elements).

**Validates: Requirements 2.1**

### Property 5: Graphiti Element Recognition
*For any* Graphiti-controlled schema element (index, label, relationship), the validator should recognize it as valid and not report it as an issue.

**Validates: Requirements 2.2, 2.4**

### Property 6: Configuration Validation Completeness
*For any* system startup, all required configuration parameters should be validated before the system begins operation.

**Validates: Requirements 3.1**

### Property 7: Configuration Error Clarity
*For any* missing or invalid configuration value, the system should report a clear error message indicating what is wrong and how to fix it.

**Validates: Requirements 3.2**

### Property 8: Configuration Default Behavior
*For any* environment variable with a defined default, accessing it when unset should return the sensible default value.

**Validates: Requirements 3.3**

### Property 9: Configuration Merge Precedence
*For any* set of multiple configuration sources, merging them should follow the correct precedence rules consistently.

**Validates: Requirements 3.5**

### Property 10: Issue Severity Categorization
*For any* issue generated by the audit system, it should be categorized with the correct severity level based on its actual impact.

**Validates: Requirements 4.2**

### Property 11: Node Modules Exclusion
*For any* issue originating from a node_modules path, it should be excluded from the main issue count in audit reports.

**Validates: Requirements 4.3**

### Property 12: Audit Determinism
*For any* codebase state, running the audit multiple times should produce consistent results with the same issues reported.

**Validates: Requirements 4.5**

## Error Handling

### Memory Validation Errors

```python
class MemoryValidationError(Exception):
    """Raised when memory structure validation fails."""
    pass

# Graceful handling
try:
    validate_l1_structure(key, data)
except MemoryValidationError as e:
    logger.warning(f"L1 validation issue (non-critical): {e}")
    # Report as LOW severity, not HIGH
```

### Schema Connection Errors

```python
# Retry logic for Neo4j connection
@retry(max_attempts=3, backoff=2.0)
async def get_actual_schema() -> Neo4jSchema:
    """Get schema with retry logic."""
    try:
        return await _fetch_schema()
    except Neo4jConnectionError:
        logger.warning("Neo4j connection failed, retrying...")
        raise
```

### Import Checker Errors

```python
# Skip files that cause errors instead of failing entire audit
try:
    check_imports(file_path)
except Exception as e:
    logger.warning(f"Skipping {file_path} due to error: {e}")
    # Continue with next file
```

## Testing Strategy

### Unit Tests

We will write unit tests for:

1. **L1 Structure Validation**
   - Test with valid L1 data
   - Test with missing optional fields
   - Test with invalid importance values
   - Test with missing required fields

2. **Schema Pattern Recognition**
   - Test Graphiti index recognition
   - Test Graphiti node label recognition
   - Test Graphiti relationship recognition

3. **Issue Filtering**
   - Test node_modules exclusion
   - Test pattern matching
   - Test configuration options

### Property-Based Tests

We will use **Hypothesis** (Python's property-based testing library) for property-based testing.

Each property-based test will:
- Run a minimum of 100 iterations
- Be tagged with a comment referencing the design document property
- Use the format: `# Feature: phase-4-improvements, Property {number}: {property_text}`

**Property Test 1: L1 Structure Consistency**
```python
from hypothesis import given, strategies as st

# Feature: phase-4-improvements, Property 1: L1 Structure Consistency
@given(
    session_id=st.uuids(),
    created_at=st.datetimes(),
    importance=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0)),
    summary=st.one_of(st.none(), st.text()),
)
def test_l1_structure_validation_property(session_id, created_at, importance, summary):
    """Property: L1 data with required fields should always validate successfully."""
    data = {
        'session_id': str(session_id),
        'created_at': created_at.isoformat(),
    }
    if importance is not None:
        data['importance'] = importance
    if summary is not None:
        data['summary'] = summary
    
    # Should not raise exception
    issues = validate_l1_structure('test_key', data)
    # Should have no critical issues
    assert all(issue.severity != Severity.CRITICAL for issue in issues)
```

**Property Test 2: Schema Validation Accuracy**
```python
# Feature: phase-4-improvements, Property 2: Schema Validation Accuracy
@given(index_name=st.sampled_from(GRAPHITI_INDEXES))
def test_graphiti_index_recognition_property(index_name):
    """Property: All Graphiti-managed indexes should be recognized as valid."""
    validator = SchemaValidator(config)
    assert validator.is_graphiti_managed(index_name) == True
```

**Property Test 3: Issue Filtering Consistency**
```python
# Feature: phase-4-improvements, Property 3: Issue Filtering Consistency
@given(
    filename=st.text(min_size=1),
    in_node_modules=st.booleans(),
)
def test_issue_filtering_property(filename, in_node_modules):
    """Property: Issues from node_modules should always be filtered out."""
    if in_node_modules:
        location = f"node_modules/some-package/{filename}"
    else:
        location = f"src/{filename}"
    
    issue = Issue(
        category=Category.IMPORTS,
        severity=Severity.HIGH,
        title="Test issue",
        description="Test",
        location=location,
        impact="Test",
        recommendation="Test",
    )
    
    filter = IssueFilter(config)
    should_include = filter.should_include(issue)
    
    # Issues in node_modules should be filtered
    if in_node_modules:
        assert should_include == False
    else:
        assert should_include == True
```

### Integration Tests

Integration tests will verify:
1. Full audit run completes successfully
2. Issue counts are accurate after filtering
3. Memory tests pass with real Redis/Neo4j
4. Schema validation works with real Graphiti schema

## Implementation Notes

### Phase 1: Memory Tester Improvements (30 minutes)
- Update L1 structure validation logic
- Make optional fields truly optional
- Improve error messages
- Add better logging

### Phase 2: Schema Validator Improvements (1 hour)
- Add Graphiti pattern recognition
- Update index checking logic
- Reduce false positives
- Document acceptable schema differences

### Phase 3: Import Checker Filtering (30 minutes)
- Add node_modules filtering
- Add configuration for exclusion patterns
- Update report generation to show filtered count

### Phase 4: Testing (1 hour)
- Write unit tests for new validation logic
- Write property-based tests
- Run full audit to verify improvements
- Update documentation

**Total Estimated Time:** 3 hours

## Success Criteria

1. MemoryTester reports 0 issues (down from 2)
2. SchemaValidator reports ≤10 issues (down from 21)
3. ImportChecker excludes node_modules from main count
4. All property-based tests pass with 100+ iterations
5. Full audit completes in <60 seconds
6. Documentation clearly explains acceptable schema differences
