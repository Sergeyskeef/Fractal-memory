"""
Pytest configuration for Fractal Memory project.

Гарантирует, что пакет `src` доступен для импортов в тестах,
даже если pytest запускается из корня проекта без установки пакета.
"""

import os
import sys


def pytest_sessionstart(session):  # type: ignore[override]
    """Добавить корень проекта в sys.path перед запуском тестов."""
    # Путь к директории tests/
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    # Корень проекта (там, где находится папка src)
    project_root = os.path.dirname(tests_dir)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

"""
Pytest configuration and fixtures.

Использование:
    pytest tests/ -v
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загрузить .env файл
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Добавить src в path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ═══════════════════════════════════════════════════════
# ASYNC SUPPORT
# ═══════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

@pytest.fixture
def config():
    """Test configuration (uses mock by default)"""
    return {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD", "test"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),  # Может быть None
        "l0_capacity": 5,
        "l1_capacity": 10,
        "importance_threshold": 0.3,
    }


# ═══════════════════════════════════════════════════════
# MOCK FIXTURES
# ═══════════════════════════════════════════════════════

@pytest.fixture
async def mock_graph():
    """Mock graph memory (no Neo4j needed)"""
    from core.graphiti_adapter import MockGraphMemory
    
    graph = MockGraphMemory()
    await graph.initialize()
    yield graph
    await graph.close()


@pytest.fixture
async def fractal_memory(config, mock_graph):
    """FractalMemory with mock backend"""
    from core.memory import FractalMemory
    
    memory = FractalMemory(config)
    memory.graph = mock_graph  # Use mock instead of real Graphiti
    await memory.initialize()
    yield memory
    await memory.close()


@pytest.fixture
async def reasoning_bank(mock_graph):
    """ReasoningBank with mock backend"""
    from core.learning import ReasoningBank
    
    bank = ReasoningBank(mock_graph, {
        "min_experiences_for_strategy": 2,
        "exploration_rate": 0.1
    })
    yield bank


# ═══════════════════════════════════════════════════════
# INTEGRATION TEST FIXTURES (require real Neo4j)
# ═══════════════════════════════════════════════════════

@pytest.fixture
async def real_graph(config):
    """
    Real Graphiti adapter (requires Neo4j).
    Skip if Neo4j not available.
    """
    from core.graphiti_adapter import GraphitiAdapter
    
    adapter = GraphitiAdapter(config)
    
    try:
        await adapter.initialize()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    
    yield adapter
    await adapter.close()


# ═══════════════════════════════════════════════════════
# MARKERS
# ═══════════════════════════════════════════════════════

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
