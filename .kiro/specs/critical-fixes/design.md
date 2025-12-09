# Design Document: Critical Bug Fixes

## Overview

This design document outlines the approach for fixing critical bugs in the Fractal Memory project that could block normal operation. The primary focus is on fixing the FractalAgent initialization issue where E2E tests fail due to incorrect parameter passing, ensuring configuration consistency across all components, and improving error handling and logging.

The fixes will maintain backward compatibility while providing clear migration paths for deprecated patterns.

## Architecture

### Current Architecture Issues

1. **FractalAgent Initialization**: Currently, `FractalAgent.__init__()` accepts only a `config` dictionary, but E2EFlowValidator tries to pass a `memory` parameter directly
2. **Configuration Inconsistency**: Different components use different parameter names and structures for the same configuration values
3. **Component Coupling**: Components create their own database connections instead of sharing instances
4. **Error Handling**: Generic error messages that don't indicate which component failed

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FractalAgent                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  __init__(config=None, memory=None, **kwargs)          │ │
│  │  - Accept both config dict and direct component params │ │
│  │  - Merge with DEFAULT_CONFIG                           │ │
│  │  - Support backward compatibility                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  initialize()                                           │ │
│  │  1. Use provided memory OR create new FractalMemory    │ │
│  │  2. Share GraphitiStore instance across components     │ │
│  │  3. Initialize retriever with shared GraphitiStore     │ │
│  │  4. Initialize reasoning with shared GraphitiStore     │ │
│  │  5. Initialize LLM client                              │ │
│  │  6. Set _initialized = True, state = IDLE              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Configuration Hierarchy

```
Environment Variables (highest priority)
    ↓
Provided Config Dict
    ↓
DEFAULT_CONFIG (lowest priority)
```

## Components and Interfaces

### 1. FractalAgent Constructor Enhancement

**Current Signature:**
```python
def __init__(self, config: Optional[Dict] = None)
```

**New Signature:**
```python
def __init__(
    self,
    config: Optional[Dict] = None,
    memory: Optional[FractalMemory] = None,
    retriever: Optional[HybridRetriever] = None,
    reasoning: Optional[ReasoningBank] = None,
    **kwargs
)
```

**Behavior:**
- If `memory` is provided, use it instead of creating new FractalMemory
- If `retriever` is provided, use it instead of creating new HybridRetriever
- If `reasoning` is provided, use it instead of creating new ReasoningBank
- Merge `kwargs` into config for backward compatibility
- Log deprecation warnings for old patterns

### 2. Configuration Unification

Create a unified configuration class that all components use:

```python
@dataclass
class UnifiedConfig:
    """Unified configuration for all components."""
    
    # Database connections
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    redis_url: str = "redis://localhost:6379"
    
    # User identity
    user_id: str = "default"
    user_name: str = "User"
    agent_name: str = "Assistant"
    
    # LLM settings
    openai_api_key: Optional[str] = None
    model: str = "gpt-5-nano-2025-08-07"
    max_tokens: int = 5000
    llm_requests_per_minute: int = 60
    
    # Memory settings
    l0_max_size: int = 500
    l1_ttl_days: int = 30
    consolidation_threshold: float = 0.8
    
    # Retrieval settings
    retrieval_limit: int = 5
    retrieval_weights: Dict[str, float] = field(default_factory=lambda: {
        "vector": 0.5,
        "keyword": 0.3,
        "graph": 0.2,
    })
    
    # Agent settings
    system_prompt: str = "..."
    save_all_messages: bool = True
    learn_from_interactions: bool = True
    
    @classmethod
    def from_dict(cls, config: Dict) -> "UnifiedConfig":
        """Create from dictionary, handling old parameter names."""
        # Map old names to new names
        param_mapping = {
            "llm_model": "model",
            # Add more mappings as needed
        }
        
        normalized = {}
        for key, value in config.items():
            new_key = param_mapping.get(key, key)
            normalized[new_key] = value
        
        return cls(**normalized)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return asdict(self)
```

### 3. Component Initialization Order

```python
async def initialize(self) -> None:
    """Initialize all components in correct order."""
    if self._initialized:
        return
    
    logger.info("Initializing FractalAgent...")
    
    try:
        # 1. Memory (or use provided)
        if self.memory is None:
            self.memory = FractalMemory(self.config)
            await self.memory.initialize()
            self._owns_memory = True
        else:
            self._owns_memory = False
            logger.info("Using provided FractalMemory instance")
        
        # 2. Retriever (or use provided, share GraphitiStore)
        if self.retriever is None:
            self.retriever = HybridRetriever(
                self.memory.graphiti,
                user_id=self.user_id,
                weights=self.config.get("retrieval_weights"),
            )
            self._owns_retriever = True
        else:
            self._owns_retriever = False
            logger.info("Using provided HybridRetriever instance")
        
        # 3. Reasoning (or use provided, share GraphitiStore)
        if self.reasoning is None:
            self.reasoning = ReasoningBank(
                self.memory.graphiti,
                self.user_id
            )
            await self.reasoning.initialize()
            self._owns_reasoning = True
        else:
            self._owns_reasoning = False
            logger.info("Using provided ReasoningBank instance")
        
        # 4. LLM client
        await self._init_llm_client()
        
        # 5. Load user context
        await self._load_user_context()
        
        self._initialized = True
        self.state = AgentState.IDLE
        logger.info(f"FractalAgent fully initialized for user {self.user_id}")
        
    except Exception as e:
        self.state = AgentState.ERROR
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        # Provide detailed error message
        component = self._identify_failed_component(e)
        raise RuntimeError(
            f"FractalAgent initialization failed at component: {component}. "
            f"Error: {str(e)}"
        ) from e
```

### 4. Enhanced Error Handling

```python
def _identify_failed_component(self, error: Exception) -> str:
    """Identify which component failed based on error."""
    error_str = str(error).lower()
    
    if "neo4j" in error_str or "graphiti" in error_str:
        return "GraphitiStore (Neo4j connection)"
    elif "redis" in error_str:
        return "RedisMemoryStore (Redis connection)"
    elif "openai" in error_str or "api key" in error_str:
        return "LLM Client (OpenAI)"
    elif "memory" in error_str:
        return "FractalMemory"
    elif "retriever" in error_str:
        return "HybridRetriever"
    elif "reasoning" in error_str:
        return "ReasoningBank"
    else:
        return "Unknown component"

async def close(self) -> None:
    """Close all connections, only for components we own."""
    logger.info("Closing FractalAgent...")
    
    # Only close components we created
    if self._owns_memory and self.memory:
        await self.memory.close()
    
    if self._owns_reasoning and self.reasoning:
        if hasattr(self.reasoning, 'close'):
            await self.reasoning.close()
    
    self._initialized = False
    self.state = AgentState.IDLE
    logger.info("FractalAgent closed")
```

## Data Models

### Configuration Model

```python
@dataclass
class ComponentConfig:
    """Configuration for a single component."""
    name: str
    required_params: List[str]
    optional_params: Dict[str, Any]
    env_var_mapping: Dict[str, str]
```

### Initialization State

```python
@dataclass
class InitializationState:
    """Track initialization state of components."""
    memory_initialized: bool = False
    retriever_initialized: bool = False
    reasoning_initialized: bool = False
    llm_initialized: bool = False
    failed_component: Optional[str] = None
    error_message: Optional[str] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Successful initialization sets correct state
*For any* valid configuration, when FractalAgent initialization completes successfully, the initialized flag should be True and state should be IDLE.
**Validates: Requirements 1.5**

### Property 2: All components initialized after successful init
*For any* valid configuration, when FractalAgent initialization completes successfully, all components (memory, retriever, reasoning, llm_client) should be non-None.
**Validates: Requirements 1.2**

### Property 3: Error messages contain component names
*For any* invalid configuration that causes initialization to fail, the error message should contain the name of the component that failed.
**Validates: Requirements 1.3, 4.1**

### Property 4: Provided memory instance is used
*For any* FractalMemory instance passed to FractalAgent, the agent should use that exact instance (same object identity) rather than creating a new one.
**Validates: Requirements 1.4**

### Property 5: Config merge preserves provided values
*For any* partial configuration dictionary, when merged with defaults, all provided values should be present in the final config and should override defaults.
**Validates: Requirements 2.3**

### Property 6: Missing required params handled correctly
*For any* configuration missing required parameters, the system should either use sensible defaults or raise a clear error indicating which parameters are missing.
**Validates: Requirements 2.4**

### Property 7: Environment variables take precedence
*For any* configuration parameter that has both an environment variable and a default value, when the environment variable is set, its value should be used instead of the default.
**Validates: Requirements 2.5**

### Property 8: GraphitiStore instance is shared
*For any* initialized FractalAgent, the GraphitiStore instance used by HybridRetriever and ReasoningBank should be the same object (same identity) as the one in FractalMemory.
**Validates: Requirements 3.2, 3.3, 3.4**

### Property 9: Close cleans up owned components
*For any* initialized FractalAgent, after calling close(), all components that were created by the agent (not provided externally) should have their close() methods called.
**Validates: Requirements 3.5**

### Property 10: Failed initialization sets ERROR state
*For any* configuration that causes initialization to fail, the agent state should be set to ERROR.
**Validates: Requirements 4.5**

### Property 11: Logs contain connection details without passwords
*For any* database connection failure, the log messages should contain the connection URI but should not contain the password.
**Validates: Requirements 4.3**

### Property 12: Test data isolation
*For any* E2EFlowValidator test run, the user_id used should be different from production user_ids to ensure data isolation.
**Validates: Requirements 5.2**

### Property 13: Test cleanup releases resources
*For any* E2EFlowValidator test run, after completion (success or failure), all database connections should be closed.
**Validates: Requirements 5.3**

### Property 14: Parallel tests don't conflict
*For any* set of tests run in parallel, each test should use isolated resources (different user_ids, separate connection pools) to prevent conflicts.
**Validates: Requirements 5.5**

### Property 15: Deprecated patterns emit warnings
*For any* use of deprecated initialization patterns, the system should emit a deprecation warning that includes the old pattern and suggested alternative.
**Validates: Requirements 6.1, 6.5**

### Property 16: Old parameter names are mapped
*For any* configuration using old parameter names, the system should automatically map them to new names and the resulting config should contain the new names.
**Validates: Requirements 6.2**

## Error Handling

### Error Categories

1. **Configuration Errors**
   - Missing required parameters
   - Invalid parameter values
   - Type mismatches
   - Action: Raise `ConfigurationError` with details

2. **Connection Errors**
   - Neo4j connection failed
   - Redis connection failed
   - Network timeouts
   - Action: Raise `ConnectionError` with component name and connection details (no passwords)

3. **Initialization Errors**
   - Component initialization failed
   - Dependency not available
   - Resource allocation failed
   - Action: Set state to ERROR, raise `InitializationError` with component name

4. **Runtime Errors**
   - LLM API failures
   - Memory operation failures
   - Retrieval failures
   - Action: Log error, return fallback response, don't crash

### Error Message Format

```python
class ComponentError(Exception):
    """Base class for component errors."""
    def __init__(self, component: str, message: str, details: Optional[Dict] = None):
        self.component = component
        self.message = message
        self.details = details or {}
        super().__init__(f"[{component}] {message}")
```

### Logging Standards

```python
# Success
logger.info(f"Component initialized: {component_name}")

# Warning
logger.warning(f"Using deprecated pattern: {old_pattern}. Use {new_pattern} instead.")

# Error with context
logger.error(
    f"Component initialization failed: {component_name}",
    extra={
        "component": component_name,
        "config": sanitized_config,  # No passwords
        "error": str(error),
    },
    exc_info=True
)
```

## Testing Strategy

### Unit Tests

Unit tests will verify specific behaviors and edge cases:

1. **Configuration Tests**
   - Test config merging with various combinations
   - Test parameter name mapping
   - Test environment variable precedence
   - Test validation of required parameters

2. **Initialization Tests**
   - Test successful initialization with minimal config
   - Test initialization with provided components
   - Test initialization failure scenarios
   - Test component ownership tracking

3. **Error Handling Tests**
   - Test error message formatting
   - Test component identification from errors
   - Test password sanitization in logs
   - Test state transitions on errors

4. **Cleanup Tests**
   - Test close() with owned components
   - Test close() with provided components
   - Test cleanup on initialization failure

### Property-Based Tests

Property-based tests will verify universal properties across many inputs using the `hypothesis` library for Python. Each test will run a minimum of 100 iterations with randomly generated inputs.

**Library:** `hypothesis` (Python)
**Configuration:** Minimum 100 iterations per property test

**Test Tagging Format:** Each property-based test must include a comment with this exact format:
```python
# Feature: critical-fixes, Property N: <property description>
```

1. **Property 1: Successful initialization state**
   - Generate random valid configs
   - Initialize FractalAgent
   - Assert _initialized == True and state == IDLE

2. **Property 2: All components initialized**
   - Generate random valid configs
   - Initialize FractalAgent
   - Assert all components are not None

3. **Property 3: Error messages contain component names**
   - Generate random invalid configs (missing params, bad URIs)
   - Try to initialize FractalAgent
   - Assert error message contains component name

4. **Property 4: Provided memory instance used**
   - Create FractalMemory with unique marker
   - Pass to FractalAgent
   - Assert agent.memory is the same object (identity check)

5. **Property 5: Config merge preserves values**
   - Generate random partial configs
   - Merge with defaults
   - Assert all provided values present and override defaults

6. **Property 8: GraphitiStore sharing**
   - Initialize FractalAgent
   - Assert retriever.graphiti is memory.graphiti (identity)
   - Assert reasoning.graphiti is memory.graphiti (identity)

7. **Property 11: Password sanitization**
   - Generate configs with passwords
   - Trigger connection failures
   - Capture logs
   - Assert logs contain URIs but not passwords

8. **Property 15: Deprecation warnings**
   - Use old initialization patterns
   - Capture warnings
   - Assert warnings contain old pattern and suggested alternative

### Integration Tests

Integration tests will verify component interactions:

1. **E2E Flow Test**
   - Initialize FractalAgent with all components
   - Execute a complete chat flow
   - Verify memory, retrieval, and reasoning work together
   - Clean up and verify resources released

2. **Configuration Integration**
   - Load config from environment
   - Initialize all components
   - Verify consistent configuration across components

3. **Error Recovery Test**
   - Trigger various failure scenarios
   - Verify system handles errors gracefully
   - Verify system can recover after fixing issues

## Implementation Notes

### Backward Compatibility Strategy

1. **Phase 1: Add new parameters** (this phase)
   - Add `memory`, `retriever`, `reasoning` parameters to `__init__`
   - Support both old and new patterns
   - Emit deprecation warnings for old patterns

2. **Phase 2: Migration period** (future)
   - Update all code to use new patterns
   - Keep deprecation warnings
   - Update documentation

3. **Phase 3: Remove deprecated patterns** (future major version)
   - Remove support for old patterns
   - Keep only new API

### Configuration Migration

Old parameter names will be automatically mapped:
```python
PARAM_MAPPING = {
    "llm_model": "model",
    "neo4j_url": "neo4j_uri",
    # Add more as discovered
}
```

### Testing Considerations

- Use `pytest` for unit and integration tests
- Use `hypothesis` for property-based tests
- Use `pytest-asyncio` for async tests
- Use `pytest-mock` for mocking components
- Use `pytest-cov` for coverage reporting

### Performance Considerations

- Initialization should complete in < 5 seconds for local connections
- Configuration merging should be O(n) where n is number of config keys
- Component sharing reduces memory usage and connection overhead
- Proper cleanup prevents resource leaks

### Security Considerations

- Never log passwords or API keys
- Sanitize all connection strings in logs
- Use environment variables for sensitive data
- Validate all configuration inputs
- Use secure defaults (e.g., require explicit password, no default API keys)
