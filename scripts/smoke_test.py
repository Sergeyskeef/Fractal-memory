#!/usr/bin/env python3
"""
Smoke test: проверка что инфраструктура работает.

Использование:
    python scripts/smoke_test.py
"""

import os
import sys
from pathlib import Path

# Добавить корень проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def check_neo4j():
    """Проверить Neo4j"""
    print("🔍 Checking Neo4j...")
    
    from neo4j import GraphDatabase
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not password:
        print("  ❌ NEO4J_PASSWORD not set")
        return False
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Проверить подключение
            result = session.run("RETURN 1 as n").single()
            assert result["n"] == 1
            print("  ✅ Connection OK")
            
            # Проверить индексы
            indexes = session.run("SHOW INDEXES YIELD name, state").data()
            online_count = sum(1 for i in indexes if i["state"] == "ONLINE")
            total_count = len(indexes)
            print(f"  ✅ Indexes: {online_count}/{total_count} ONLINE")
            
            # Проверить миграции
            migrations = session.run(
                "MATCH (m:Migration) RETURN count(m) as count"
            ).single()["count"]
            print(f"  ✅ Migrations applied: {migrations}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_redis():
    """Проверить Redis"""
    print("🔍 Checking Redis...")
    
    import redis
    
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        r = redis.from_url(url)
        
        # Ping
        assert r.ping()
        print("  ✅ Connection OK")
        
        # Read/Write
        r.set("_smoke_test", "ok")
        value = r.get("_smoke_test")
        assert value == b"ok"
        r.delete("_smoke_test")
        print("  ✅ Read/Write OK")
        
        # Persistence
        info = r.info("persistence")
        aof = "enabled" if info.get("aof_enabled", 0) else "disabled"
        print(f"  ✅ AOF persistence: {aof}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("=" * 50)
    print("🧪 SMOKE TEST: Fractal Memory Infrastructure")
    print("=" * 50)
    print()
    
    results = []
    
    results.append(("Neo4j", check_neo4j()))
    print()
    results.append(("Redis", check_redis()))
    
    print()
    print("=" * 50)
    print("📊 RESULTS:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! Infrastructure is ready.")
        return 0
    else:
        print("⚠️  Some checks failed. Fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
