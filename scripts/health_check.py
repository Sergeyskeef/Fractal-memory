#!/usr/bin/env python3
"""
Health checks для Fractal Memory System.

Проверяет:
- Подключение к Neo4j
- Подключение к Redis
- Наличие индексов Neo4j
- Статус индексов (должны быть ONLINE)

Использование:
    python scripts/health_check.py
"""

import os
import sys
from pathlib import Path

# Добавить корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from dotenv import load_dotenv
import redis

load_dotenv()


def check_neo4j():
    """Проверка Neo4j"""
    print("🔍 Checking Neo4j...")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not password:
        print("  ❌ NEO4J_PASSWORD not set in .env")
        return False
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Проверить подключение
            result = session.run("RETURN 1 as n").single()
            if result["n"] != 1:
                print("  ❌ Connection test failed")
                return False
            
            print("  ✅ Connection OK")
            
            # Проверить индексы
            indexes = session.run("SHOW INDEXES YIELD name, state, populationPercent").data()
            
            if not indexes:
                print("  ⚠️  No indexes found (create them with scripts/create_indexes.cypher)")
            else:
                online_count = sum(1 for i in indexes if i["state"] == "ONLINE")
                total_count = len(indexes)
                print(f"  ✅ Indexes: {online_count}/{total_count} ONLINE")
                
                # Показать индексы не в состоянии ONLINE
                not_online = [i for i in indexes if i["state"] != "ONLINE"]
                if not_online:
                    print("  ⚠️  Indexes not ONLINE:")
                    for idx in not_online:
                        print(f"     - {idx['name']}: {idx['state']}")
            
            # Проверить миграции
            migrations = session.run(
                "MATCH (m:Migration) RETURN count(m) as count"
            ).single()["count"]
            print(f"  ✅ Migrations applied: {migrations}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Neo4j check failed: {e}")
        return False


def check_redis():
    """Проверка Redis"""
    print("🔍 Checking Redis...")
    
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        r = redis.from_url(url)
        
        # Проверить подключение
        if not r.ping():
            print("  ❌ Redis ping failed")
            return False
        
        print("  ✅ Connection OK")
        
        # Проверить запись/чтение
        r.set("health_check", "ok", ex=10)
        value = r.get("health_check")
        if value != b"ok":
            print("  ❌ Read/write failed")
            return False
        
        r.delete("health_check")
        print("  ✅ Read/Write OK")
        
        # Проверить persistence
        info = r.info("persistence")
        aof_enabled = info.get("aof_enabled", 0)
        print(f"  ✅ AOF persistence: {'enabled' if aof_enabled else 'disabled'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Redis check failed: {e}")
        return False


def main():
    print("=" * 60)
    print("🏥 HEALTH CHECK: Fractal Memory System")
    print("=" * 60)
    print()
    
    results = []
    
    # Проверка Neo4j
    results.append(("Neo4j", check_neo4j()))
    print()
    
    # Проверка Redis
    results.append(("Redis", check_redis()))
    print()
    
    # Итоги
    print("=" * 60)
    print("📊 RESULTS:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All health checks passed! System is ready.")
        return 0
    else:
        print("⚠️  Some health checks failed. Fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

