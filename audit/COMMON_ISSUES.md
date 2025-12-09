# Common Issues and Fixes

This document describes common issues found by the audit system and how to fix them.

## Import Issues

### Missing Python Modules

**Issue:** `ImportError: module 'graphiti_adapter' not found`

**Cause:** Code imports a module that doesn't exist or has been removed.

**Fix:**
1. Check if the module was renamed or moved
2. Update the import statement
3. If the module was removed, refactor code to not use it

**Example:**
```python
# Bad
from src.core.graphiti_adapter import GraphitiAdapter

# Good
from src.core.graphiti_store import GraphitiStore
```

### Missing TypeScript Modules in node_modules

**Issue:** `Missing TypeScript module: ./types-DZOqTgiN.js`

**Cause:** TypeScript build artifacts or internal module references in dependencies.

**Fix:** These are usually in `node_modules/` and can be ignored. Focus on issues in your own code.

**Filter:** Look for issues where location does NOT contain `node_modules/`.

### Circular Dependencies

**Issue:** `Circular dependency: A → B → A`

**Cause:** Two or more modules import each other, creating a cycle.

**Fix:**
1. Extract shared code to a third module
2. Use dependency injection
3. Refactor to remove the circular dependency

**Example:**
```python
# Bad
# file_a.py
from file_b import B

# file_b.py
from file_a import A

# Good
# file_a.py
from file_c import shared_function

# file_b.py
from file_c import shared_function

# file_c.py
def shared_function():
    pass
```

## Schema Issues

### Non-existent Node Fields

**Issue:** `Field 'deleted' does not exist on :Episodic nodes`

**Cause:** Code tries to access a field that doesn't exist in the actual Neo4j schema.

**Fix:**
1. Check the actual schema with `CALL db.schema.nodeTypeProperties()`
2. Update code to use correct field names
3. Or add the field to the schema via migration

**Example:**
```python
# Bad
MATCH (e:Episodic)
WHERE e.deleted = false
RETURN e

# Good (if using soft delete pattern)
MATCH (e:Episodic)
WHERE NOT e:Deleted
RETURN e

# Or (if field exists)
MATCH (e:Episodic)
WHERE e.is_deleted = false
RETURN e
```

### Missing Node Labels

**Issue:** `Expected node label :ShortTerm not found in schema`

**Cause:** Code references a node label that doesn't exist in Neo4j.

**Fix:**
1. Check if the label was renamed (e.g., :ShortTerm → :Episodic)
2. Update code to use correct label
3. Or create the label via migration

**Example:**
```python
# Bad
MATCH (s:ShortTerm)
RETURN s

# Good
MATCH (e:Episodic)
WHERE e.level = 'short_term'
RETURN e
```

### Missing Relationships

**Issue:** `Relationship type 'HAS_MEMORY' not found`

**Cause:** Code uses a relationship type that doesn't exist.

**Fix:**
1. Check actual relationship types with `CALL db.relationshipTypes()`
2. Update code to use correct relationship type
3. Or create the relationship via migration

**Example:**
```python
# Bad
MATCH (u:User)-[r:HAS_MEMORY]->(m:Memory)
RETURN m

# Good
MATCH (u:User)-[r:CREATED]->(e:Episodic)
RETURN e
```

## API Issues

### SearchResult Format Inconsistency

**Issue:** `SearchResult missing required field: metadata`

**Cause:** Different components use different SearchResult formats.

**Fix:**
1. Define a single SearchResult dataclass/interface
2. Ensure all components use the same definition
3. Add missing fields

**Example:**
```python
# Good - Single definition
@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    metadata: Dict[str, Any]
```

### Missing API Methods

**Issue:** `FractalMemory missing method: consolidate`

**Cause:** Required method not implemented in the class.

**Fix:**
1. Implement the missing method
2. Or update callers to use a different method

**Example:**
```python
class FractalMemory:
    async def consolidate(self):
        """Consolidate memories between levels."""
        await self._consolidate_l0_to_l1()
        await self._consolidate_l1_to_l2()
```

## Memory Issues

### L0→L1 Consolidation Problems

**Issue:** `No L1 keys found in Redis`

**Cause:** Consolidation not running or not creating L1 keys.

**Fix:**
1. Check consolidation logic is being called
2. Verify L1 key format: `memory:{user}:l1:session:{id}`
3. Check importance threshold for consolidation

**Example:**
```python
async def consolidate_l0_to_l1(self):
    # Get high-importance items from L0
    l0_items = await self.get_l0_items(min_importance=0.5)
    
    for item in l0_items:
        # Create L1 session
        session_id = str(uuid.uuid4())
        l1_key = f"memory:{item.user_id}:l1:session:{session_id}"
        
        # Store in L1
        await self.redis.hset(l1_key, mapping={
            'session_id': session_id,
            'summary': item.content,
            'importance': str(item.importance),
            'created_at': datetime.now().isoformat(),
        })
```

### L1→L2 Consolidation Problems

**Issue:** `No Episodic nodes found in Neo4j`

**Cause:** L1→L2 consolidation not running or not creating nodes.

**Fix:**
1. Check consolidation logic is being called
2. Verify Graphiti integration
3. Check importance threshold

**Example:**
```python
async def consolidate_l1_to_l2(self):
    # Get high-importance L1 sessions
    l1_sessions = await self.get_l1_sessions(min_importance=0.7)
    
    for session in l1_sessions:
        # Add to Graphiti (creates Episodic + Entity nodes)
        await self.graphiti_store.add_episode(
            content=session.summary,
            user_id=session.user_id,
            metadata={'importance': session.importance}
        )
        
        # Mark as promoted
        await self.redis.hset(session.key, 'promoted_to_l2', 'True')
```

## Frontend Issues

### TypeScript Type Mismatch

**Issue:** `TypeScript type ChatResponse missing field: timestamp`

**Cause:** Frontend types don't match backend models.

**Fix:**
1. Update TypeScript types to match backend
2. Or update backend to include missing fields

**Example:**
```typescript
// types.ts
interface ChatResponse {
    message: string;
    user_id: string;
    timestamp: string;  // Add missing field
    memory_stats: MemoryStats;
}
```

### CORS Not Configured

**Issue:** `CORS middleware not configured`

**Cause:** Backend doesn't allow frontend origin.

**Fix:**
1. Add CORS middleware to FastAPI app
2. Configure allowed origins

**Example:**
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Missing Error Handling

**Issue:** `Component missing error handling: InputArea.tsx`

**Cause:** Component makes API calls but doesn't handle errors.

**Fix:**
1. Add try/catch blocks
2. Add error state
3. Display errors to user

**Example:**
```typescript
const [error, setError] = useState<string | null>(null);

const handleSubmit = async () => {
    try {
        setError(null);
        const response = await api.sendMessage(message);
        // Handle success
    } catch (err) {
        setError(err.message);
        console.error('Failed to send message:', err);
    }
};
```

## Configuration Issues

### Missing Environment Variables

**Issue:** `Missing required environment variable: NEO4J_PASSWORD`

**Cause:** .env file missing or incomplete.

**Fix:**
1. Copy .env.example to .env
2. Fill in all required values

**Example:**
```bash
# .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_actual_password
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-your-actual-key
```

### Placeholder Values

**Issue:** `Placeholder value in NEO4J_PASSWORD`

**Cause:** .env file has example/placeholder values.

**Fix:**
1. Replace placeholders with actual values
2. Never commit real credentials to git

**Example:**
```bash
# Bad
NEO4J_PASSWORD=your_password_here

# Good
NEO4J_PASSWORD=actual_secure_password_123
```

### Docker Compose Issues

**Issue:** `Neo4j volumes not configured`

**Cause:** docker-compose.yml doesn't persist data.

**Fix:**
1. Add volumes to docker-compose.yml
2. Data will persist across container restarts

**Example:**
```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    ports:
      - "7687:7687"
      - "7474:7474"

volumes:
  neo4j_data:
  neo4j_logs:
```

## Integration Issues

### Chat Flow Broken

**Issue:** `Cannot retrieve stored message`

**Cause:** Message stored but not indexed or searchable.

**Fix:**
1. Check indexing is working
2. Verify search implementation
3. Add delay for indexing if needed

**Example:**
```python
# Store message
message_id = await memory.remember(content, user_id=user_id)

# Wait for indexing (if needed)
await asyncio.sleep(0.5)

# Search should now work
results = await memory.search(query=content[:20], user_id=user_id)
```

### Memory Not Persisting

**Issue:** `Data not retrievable after restart`

**Cause:** Data not saved to persistent storage (Neo4j).

**Fix:**
1. Ensure consolidation runs before shutdown
2. Check data is in Neo4j, not just Redis
3. Verify Neo4j volumes are configured

**Example:**
```python
async def shutdown(self):
    # Consolidate before shutdown
    await self.consolidate()
    
    # Close connections
    await self.close()
```

## Performance Issues

### Slow Audit Execution

**Issue:** Audit takes too long to complete.

**Fix:**
1. Use `--static-only` to skip runtime tests
2. Run checkers in parallel (default)
3. Increase timeout values if needed

**Example:**
```bash
# Fast audit (static only)
python -m audit.main --static-only

# Full audit with increased timeout
python -m audit.main --full --timeout 60
```

### Too Many Import Issues

**Issue:** Hundreds of import issues in node_modules.

**Fix:**
1. Filter issues by location
2. Focus on issues in your own code
3. Ignore node_modules issues

**Example:**
```python
# Filter issues in report
own_code_issues = [
    issue for issue in all_issues
    if 'node_modules' not in issue.location
]
```

## Best Practices

### Regular Audits

Run audits regularly to catch issues early:

```bash
# Before committing
python -m audit.main --static-only

# Before deploying
python -m audit.main --full

# In CI/CD
python -m audit.main --full --output-format json
```

### Fix Priority

Fix issues in this order:

1. **Critical** - System doesn't work
2. **High** - Serious problems
3. **Medium** - Important but not urgent
4. **Low** - Nice to have

### Incremental Fixes

Don't try to fix everything at once:

1. Run audit
2. Fix critical issues
3. Run audit again
4. Fix high priority issues
5. Repeat

### Documentation

Document fixes and patterns:

1. Update this file with new issues
2. Add examples of fixes
3. Share knowledge with team
