"""
Forensic inspector: dump L1 (Redis), L2/L3 (Neo4j), Reasoning (Experience).

Usage:
    python3 scripts/inspect_everything.py
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis


def ensure_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


async def inspect_redis(user_id: str, redis_url: str) -> None:
    print("\n📦 L1 (Redis) summaries")
    client = redis.from_url(redis_url, decode_responses=True)
    key = f"memory:{user_id}:l1:summary:list"
    try:
        items = await client.lrange(key, 0, -1)
    except Exception as exc:
        print(f"❌ Redis read failed: {exc}")
        return
    if not items:
        print("  (empty)")
        return
    for idx, raw in enumerate(items):
        try:
            parsed: Dict[str, Any] = json.loads(raw)
        except Exception:
            parsed = {"summary": raw}
        created = parsed.get("created_at", "n/a")
        content = (parsed.get("summary") or "").replace("\n", " ")
        preview = content[:120] + ("..." if len(content) > 120 else "")
        print(f"  [{idx}] Time: {created} | {preview}")


async def inspect_neo4j(user_id: str, uri: str, user: str, password: str) -> None:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            print("\n🕸️  L2 (Episodic)")
            res = await session.run("MATCH (n:Episodic) RETURN n")
            rows = [r async for r in res]
            if not rows:
                print("  (empty)")
            for r in rows:
                n = r["n"]
                uuid = n.get("uuid") or n.get("id") or "n/a"
                created = n.get("created_at") or n.get("createdAt") or n.get("created") or "n/a"
                scale = n.get("scale", "n/a")
                content = (n.get("content") or "").replace("\n", " ")
                preview = content[:140] + ("..." if len(content) > 140 else "")
                print(f"  UUID={uuid} | Created={created} | Scale={scale} | {preview}")

            print("\n🏷️  L3 (Entities)")
            res = await session.run("MATCH (n:Entity) RETURN n")
            rows = [r async for r in res]
            if not rows:
                print("  (empty)")
            for r in rows:
                n = r["n"]
                name = n.get("name") or "n/a"
                etype = n.get("type") or n.get("label") or "n/a"
                desc = (n.get("description") or n.get("content") or "").replace("\n", " ")
                preview = desc[:120] + ("..." if len(desc) > 120 else "")
                print(f"  {name} | type={etype} | {preview}")

            print("\n🧠 Reasoning (Experience)")
            res = await session.run("MATCH (n:Experience) RETURN n")
            rows = [r async for r in res]
            print(f"  Total: {len(rows)}")
            for r in rows[:5]:
                n = r["n"]
                outcome = n.get("outcome", "n/a")
                ts = n.get("created_at") or "n/a"
                print(f"    id={n.get('id','n/a')} outcome={outcome} created_at={ts}")
    except Exception as exc:
        print(f"❌ Neo4j inspection failed: {exc}")
    finally:
        await driver.close()


async def main() -> None:
    load_dotenv()
    ensure_path()

    user_id = os.getenv("USER_ID", "sergey")
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    await inspect_redis(user_id, redis_url)
    await inspect_neo4j(user_id, neo4j_uri, neo4j_user, neo4j_password)


if __name__ == "__main__":
    asyncio.run(main())
