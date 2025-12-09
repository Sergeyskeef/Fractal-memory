"""Unit tests for GraphitiStore behaviour (without Neo4j)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.graphiti_store import GraphitiStore


@pytest.mark.asyncio
async def test_graphiti_store_connect_uses_graphiti(monkeypatch):
    graphiti_instance = AsyncMock()
    graphiti_instance.build_indices_and_constraints = AsyncMock()
    GraphitiMock = MagicMock(return_value=graphiti_instance)
    monkeypatch.setattr("src.core.graphiti_store.Graphiti", GraphitiMock)

    store = GraphitiStore(
        neo4j_uri="bolt://mock:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        user_id="tester",
    )
    await store.connect()

    GraphitiMock.assert_called_once()
    assert store.graphiti is graphiti_instance
    # indices building should be handled outside connect
    assert graphiti_instance.build_indices_and_constraints.await_count == 0


@pytest.mark.asyncio
async def test_graphiti_store_add_episode_tags_user(monkeypatch):
    graphiti_instance = AsyncMock()
    episode_mock = MagicMock()
    episode_mock.episode.uuid = "uuid-123"
    graphiti_instance.add_episode.return_value = episode_mock
    store = GraphitiStore(
        neo4j_uri="bolt://mock:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        user_id="tester",
    )
    store.graphiti = graphiti_instance

    episode_id = await store.add_episode("Content", 0.9, source="unit")

    assert episode_id == "uuid-123"
    args, kwargs = graphiti_instance.add_episode.call_args
    assert "[user:tester]" in kwargs["episode_body"]

