# Fractal Memory Project Audit System

Comprehensive audit system for the Fractal Memory project. This system performs static analysis, runtime testing, and integration validation to ensure code quality and system correctness.

## Overview

The audit system consists of three main phases:

1. **Static Analysis** - Code analysis without execution
   - Import validation
   - Schema validation
   - API consistency checks
   - Frontend-backend compatibility
   - Configuration validation

2. **Runtime Testing** - Tests with real databases
   - Memory system testing (L0→L1→L2→L3)
   - Retrieval and search testing
   - Learning system testing

3. **Integration Testing** - End-to-end validation
   - Full chat flow testing
   - Memory persistence testing
   - Learning flow testing

## Quick Start

### Prerequisites

- Python 3.10+
- Neo4j database running
- Redis running
- Environment variables configured

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start databases
docker compose up -d neo4j redis
```

### Basic Usage

```bash
# Run full audit
python -m audit.main --full

# Run only static analysis (no database required)
python -m audit.main --static-only

# Run only runtime tests
python -m audit.main --runtime-only

# Generate JSON report
python -m audit.main --full --output-format json

# Save to custom file
python -m audit.main --full --output-file my_report.md

# Verbose output
python -m audit.main --full --verbose
```

## Configuration

Create a `.env` file in the project root:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Redis Configuration
REDIS_URL=redis://localhost:6379

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your_api_key
```

## Components

### Phase 1: Static Checkers

#### ImportChecker
Validates all Python and TypeScript imports.

**Checks:**
- Missing modules
- Incorrect import paths
- Circular dependencies
- Version compatibility

#### SchemaValidator
Validates code against actual Neo4j schema.

**Checks:**
- Non-existent node fields
- Incorrect node labels
- Invalid relationship types
- Missing indexes

#### APIValidator
Checks API consistency between components.

**Checks:**
- SearchResult format consistency
- FractalMemory API compatibility
- HybridRetriever API compatibility
- FastAPI endpoint formats

#### FrontendValidator
Validates React/TypeScript integration with backend.

**Checks:**
- TypeScript types match FastAPI models
- CORS configuration
- Error handling in components
- API endpoint usage

#### ConfigValidator
Validates system configuration.

**Checks:**
- Environment variables
- Docker Compose configuration
- Database migrations
- Backend configuration

### Phase 2: Runtime Testers

#### MemoryTester
Tests memory system with real databases.

**Tests:**
- L0→L1 consolidation (Redis→Redis)
- L1→L2 consolidation (Redis→Neo4j)
- Decay logic (importance decreases over time)
- Garbage collection (safe deletion)
- Deduplication (no duplicates in L2)

#### RetrievalTester
Tests search and retrieval functionality.

**Tests:**
- Vector search (Graphiti embeddings)
- Keyword search (Neo4j fulltext)
- Graph search (relationship traversal)
- L0/L1 search (Redis)
- RRF fusion (result merging)

#### LearningTester
Tests ReasoningBank and learning system.

**Tests:**
- Strategy creation (:Strategy nodes)
- Experience logging (:Experience nodes)
- Confidence updates (success_rate)
- Strategy retrieval
- Agent integration

### Phase 3: Integration Testers

#### E2EFlowValidator
Tests complete system flows.

**Tests:**
- Full chat flow (message → search → respond → save → learn)
- Memory persistence (data survives restart)
- Learning flow (strategies used in chat)

## Report Format

### Markdown Report

```markdown
# Fractal Memory Project Audit Report

## Executive Summary
- Total Issues: X
- 🔴 Critical: Y
- 🟠 High: Z
- 🟡 Medium: W
- 🟢 Low: V

## Issues by Category
- imports: N
- schema: M
...

## Test Results
### ImportChecker - ✅ PASSED
Duration: 123.45ms
Issues: 0

## 🔴 Critical Issues
[Detailed issue descriptions]

## 🟠 High Priority Issues
[Detailed issue descriptions]

## Recommendations
1. Fix critical import errors
2. Update code to match Neo4j schema
...
```

### JSON Report

Machine-readable format for automation:

```json
{
  "timestamp": "2025-12-06T12:00:00",
  "total_issues": 100,
  "issues_by_severity": {
    "critical": 5,
    "high": 30,
    "medium": 50,
    "low": 15
  },
  "test_results": [...],
  "all_issues": [...],
  "recommendations": [...]
}
```

## Severity Levels

- 🔴 **CRITICAL** - System doesn't work or works incorrectly
- 🟠 **HIGH** - Serious problem, requires fixing
- 🟡 **MEDIUM** - Medium priority issue
- 🟢 **LOW** - Minor issue or improvement

## Issue Categories

- **imports** - Import problems
- **schema** - Neo4j schema problems
- **api** - API consistency problems
- **memory** - Memory system problems
- **retrieval** - Search and retrieval problems
- **learning** - Learning system problems
- **integration** - Integration problems
- **frontend** - Frontend problems
- **config** - Configuration problems

## Troubleshooting

### "No Neo4j credentials found"

**Solution:** Set environment variable:
```bash
export NEO4J_PASSWORD=your_password
```

### "Cannot connect to Neo4j"

**Solution:**
```bash
# Start Neo4j
docker compose up -d neo4j

# Check if running
docker ps | grep neo4j
```

### "Cannot connect to Redis"

**Solution:**
```bash
# Start Redis
docker compose up -d redis

# Check if running
docker ps | grep redis
```

### "Import errors in node_modules"

**Solution:** This is expected. Focus on issues in your own code (not in `node_modules/`).

### "Too many issues found"

**Solution:**
1. Focus on critical and high priority issues first
2. Use `--static-only` to skip runtime tests initially
3. Filter issues by category in the report
4. Fix issues incrementally and re-run audit

## Advanced Usage

### Programmatic Usage

```python
import asyncio
from audit.config import AuditConfig
from audit.checkers.import_checker import ImportChecker
from audit.reports.generator import ReportGenerator

async def main():
    config = AuditConfig()
    
    # Run specific checker
    checker = ImportChecker(config)
    result = await checker.run()
    
    # Generate report
    generator = ReportGenerator()
    report_path = generator.generate_report(
        test_results=[result],
        duration_seconds=10.5,
        format="markdown"
    )
    
    print(f"Report: {report_path}")

asyncio.run(main())
```

### Custom Checkers

```python
from audit.core.base_checker import StaticChecker
from audit.core.models import Issue, Category, Severity

class MyCustomChecker(StaticChecker):
    def __init__(self, config):
        super().__init__(name="MyCustomChecker")
        self.config = config
    
    async def _check(self) -> List[Issue]:
        issues = []
        
        # Your validation logic here
        if some_condition:
            issues.append(self.create_issue(
                category=Category.CUSTOM,
                severity=Severity.HIGH,
                title="Custom issue found",
                description="Description of the issue",
                location="file.py:123",
                impact="Impact on the system",
                recommendation="How to fix it",
            ))
        
        return issues
```

### Parallel Execution

```python
from audit.orchestrator import AuditOrchestrator
from audit.config import AuditConfig

config = AuditConfig()
orchestrator = AuditOrchestrator(config)

# Run with optimization (groups by dependencies)
results = await orchestrator.run_optimized(checkers)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Project Audit
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    
    services:
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run audit
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: testpassword
          REDIS_URL: redis://localhost:6379
        run: |
          python -m audit.main --full --output-format json --output-file audit_report.json
      
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: audit-report
          path: audit_report.json
      
      - name: Check for critical issues
        run: |
          python -c "import json; report = json.load(open('audit_report.json')); exit(1 if report['issues_by_severity'].get('critical', 0) > 0 else 0)"
```

## Project Structure

```
audit/
├── __init__.py
├── README.md
├── main.py               # CLI interface
├── run_audit.py          # Legacy script
├── config.py             # Configuration
├── orchestrator.py       # Parallel execution
├── core/                 # Base classes
│   ├── base_checker.py   # BaseChecker, StaticChecker, RuntimeTester
│   └── models.py         # Issue, TestResult, AuditReport
├── checkers/             # Static analysis
│   ├── import_checker.py
│   ├── schema_validator.py
│   ├── api_validator.py
│   ├── frontend_validator.py
│   └── config_validator.py
├── testers/              # Runtime tests
│   ├── memory_tester.py
│   ├── retrieval_tester.py
│   ├── learning_tester.py
│   ├── e2e_validator.py
│   └── test_*.py         # Property-based tests
└── reports/              # Report generation
    └── generator.py
```

## Contributing

To add new checkers or testers:

1. Create a new file in `audit/checkers/` or `audit/testers/`
2. Extend `StaticChecker` or `RuntimeTester`
3. Implement the `_check()` method
4. Add to the appropriate phase in `audit/main.py`
5. Update this documentation

## Next Steps

After running the audit:

1. Review the generated report in `audit_reports/`
2. Fix critical and high priority issues first
3. Re-run audit to verify fixes
4. Address medium and low priority issues
5. Set up CI/CD integration for continuous auditing
