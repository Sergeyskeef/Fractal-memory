"""Unit tests for internal helpers of FractalMemory."""

import pytest

from src.core.memory import FractalMemory, MemoryItem


class DummyGraphiti:
    async def execute_cypher(self, query, params):
        snippet = params.get("snippet", "")
        if "duplicate" in snippet:
            return [{"cnt": 1}]
        return [{"cnt": 0}]


@pytest.fixture
def memory():
    return FractalMemory({"user_id": "tester"})


def test_contains_key_facts_detects_personal_info(memory):
    item = MemoryItem(id="1", content="Меня зовут Сергей")
    assert memory._contains_key_facts(item) is True

    neutral = MemoryItem(id="2", content="Просто факт без маркеров")
    assert memory._contains_key_facts(neutral) is False


def test_calculate_importance_decay(memory):
    item = MemoryItem(id="1", content="Test", importance=0.8, access_count=3, level=0)
    updated = memory._calculate_importance(item, age_minutes=30)
    assert 0.0 < updated <= 1.0


@pytest.mark.asyncio
async def test_is_duplicate_in_l2(memory):
    memory.graphiti = DummyGraphiti()
    dup_item = MemoryItem(id="1", content="duplicate fact for tester")
    unique_item = MemoryItem(id="2", content="brand new insight")

    assert await memory._is_duplicate_in_l2(dup_item) is True
    assert await memory._is_duplicate_in_l2(unique_item) is False

