"""
Полная очистка Redis и Neo4j (Graphiti) для ручного тестирования.

Usage:
    python3 scripts/wipe_all.py

Требуются переменные окружения (.env):
    REDIS_URL
    NEO4J_URI
    NEO4J_USER
    NEO4J_PASSWORD
    USER_ID (опционально, по умолчанию "default")
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.core.redis_store import RedisMemoryStore
from src.core.graphiti_store import GraphitiStore


async def main():
    load_dotenv()

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    user_id = os.getenv("USER_ID", "default")

    if not neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD is required to wipe Neo4j")

    # Redis wipe
    print("🗑️  Wiping Redis...")
    redis_store = RedisMemoryStore(redis_url, user_id=user_id)
    await redis_store.connect()
    try:
        await redis_store.client.flushall()  # type: ignore[attr-defined]
    finally:
        await redis_store.close()

    # Neo4j wipe
    print("🗑️  Wiping Neo4j (Graphiti)...")
    graphiti = GraphitiStore(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        user_id=user_id,
    )
    await graphiti.connect()
    try:
        await graphiti.execute_cypher("MATCH (n) DETACH DELETE n")
    finally:
        await graphiti.close()

    print("✨ Clean slate. Ready for testing.")


if __name__ == "__main__":
    asyncio.run(main())
