"""
Reset memory: Redis FLUSHALL + Neo4j DETACH DELETE.

Usage:
    python3 scripts/reset_memory.py
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis


def ensure_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


async def wipe_redis(redis_url: str) -> None:
    client = redis.from_url(redis_url, decode_responses=True)
    await client.flushall()
    await client.aclose()
    print("🗑️  Redis flushed (FLUSHALL)")


async def wipe_neo4j(uri: str, user: str, password: str) -> None:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("🗑️  Neo4j wiped (DETACH DELETE n)")
    finally:
        await driver.close()


async def main() -> None:
    load_dotenv()
    ensure_path()

    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    await wipe_redis(redis_url)
    await wipe_neo4j(neo4j_uri, neo4j_user, neo4j_password)
    print("✅ Memory Wiped Successfully")


if __name__ == "__main__":
    asyncio.run(main())
