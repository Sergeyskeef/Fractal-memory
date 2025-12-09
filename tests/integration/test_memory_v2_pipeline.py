import asyncio
import os
import pytest

from src.agent import FractalAgent
from src.core.memory import FractalMemory


def _build_config():
    return {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "user_id": "test_user_v2",
        "l0_consolidation_batch": 15,
        "auto_consolidate_l0": False,  # делаем детерминированным для тестов
    }


async def _ensure_services():
    cfg = _build_config()

    # Redis — обязателен
    import redis.asyncio as redis  # type: ignore

    try:
        r = redis.from_url(cfg["redis_url"])
        await r.ping()
        await r.flushdb()
    finally:
        await r.close()

    # Neo4j — если нет пароля, пропускаем
    if not cfg.get("neo4j_password"):
        pytest.skip("NEO4J_PASSWORD not set")

    return cfg


async def _clean_neo4j(cfg):
    from src.core.graphiti_store import GraphitiStore

    store = GraphitiStore(
        neo4j_uri=cfg["neo4j_uri"],
        neo4j_user=cfg["neo4j_user"],
        neo4j_password=cfg["neo4j_password"],
        user_id=cfg["user_id"],
    )
    await store.connect()
    try:
        await store.execute_cypher(
            """
            MATCH (ep:Episodic)
            WHERE ep.content CONTAINS $tag
            DETACH DELETE ep
            """,
            {"tag": f"[user:{cfg['user_id']}]"},
        )
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_golden_flow_15_to_1():
    cfg = await _ensure_services()
    await _clean_neo4j(cfg)
    try:
        agent = FractalAgent(cfg)
        await agent.initialize()
    except Exception as e:
        pytest.skip(f"Neo4j/Graphiti unavailable: {e}")

    try:
        # 20 сообщений → 1 батч → 1 summary → 1 L2
        messages = [str(i) for i in range(1, 21)]
        for msg in messages:
            await agent.chat(msg)

        result = await agent.memory.consolidate()
        assert result.promoted == 1

        summaries = await agent.memory.redis_store.l1_get_recent_summaries(10)
        assert len(summaries) == 1

        l2 = await agent.memory.graphiti.execute_cypher(
            """
            MATCH (ep:Episodic)
            WHERE ep.content CONTAINS $tag
            RETURN count(ep) as cnt
            """,
            {"tag": f"[user:{cfg['user_id']}]"},
        )
        assert l2 and l2[0].get("cnt", 0) == 1
    finally:
        await agent.close()


@pytest.mark.asyncio
async def test_race_condition_single_batch():
    cfg = await _ensure_services()
    await _clean_neo4j(cfg)
    try:
        memory = FractalMemory(cfg)
        await memory.initialize()
    except Exception as e:
        pytest.skip(f"Neo4j/Graphiti unavailable: {e}")

    try:
        # 20 записей в L0
        for i in range(20):
            await memory.remember(f"msg {i}", importance=0.6)

        # Пять параллельных консолидаций — должна пройти только одна
        tasks = [memory._consolidate_l0_to_l1_locked() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        promoted = sum(r.promoted for r in results)
        assert promoted == 1
    finally:
        await memory.close()


@pytest.mark.asyncio
async def test_context_zoom_contains_l0_and_l1():
    cfg = await _ensure_services()
    await _clean_neo4j(cfg)
    try:
        agent = FractalAgent(cfg)
        await agent.initialize()
    except Exception as e:
        pytest.skip(f"Neo4j/Graphiti unavailable: {e}")

    try:
        # Наполняем L0 до порога батча, чтобы гарантировать появление summary в L1
        for i in range(cfg["l0_consolidation_batch"]):
            await agent.memory.remember(f"raw-{i}", importance=0.5)
        # Создать один summary
        await agent.memory.consolidate()

        # Отключаем Graphiti поиск, чтобы проверить каскад L0/L1 без ошибок Cypher
        from unittest.mock import AsyncMock
        agent.retriever.search = AsyncMock(return_value=[])

        ctx = await agent._retrieve_context("raw")
        sources = []
        for c in ctx:
            if hasattr(c, "source"):
                sources.append(c.source)
            elif isinstance(c, dict) and "source" in c:
                sources.append(c["source"])

        assert any(s == "l0_raw" for s in sources)
        assert any(s == "l1_summary" for s in sources)
    finally:
        await agent.close()
