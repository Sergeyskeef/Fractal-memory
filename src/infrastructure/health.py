"""
Health checks для всех компонентов.
"""

from typing import Dict
import asyncio
import inspect
import time
import logging

from src.infrastructure.retry import retry_async

logger = logging.getLogger(__name__)


@retry_async(max_attempts=3, base_delay=0.2)
async def check_neo4j(graph) -> Dict:
    """Проверка Neo4j"""
    try:
        start_time = time.time()
        result = await graph.execute_cypher("RETURN 1 as n", {})
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@retry_async(max_attempts=3, base_delay=0.2)
async def check_redis(redis_client) -> Dict:
    """
    Проверка Redis.
    Поддерживает и sync, и async клиентов.
    """
    start_time = time.time()
    try:
        # Определить, является ли ping корутиной
        ping_method = getattr(redis_client, "ping", None)
        if ping_method is None:
            raise AttributeError("Redis client has no 'ping' method")

        if asyncio.iscoroutinefunction(ping_method) or inspect.iscoroutinefunction(ping_method):
            # Async‑клиент
            await ping_method()
        else:
            # Sync‑клиент
            ping_method()

        latency_ms = (time.time() - start_time) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def full_health_check(components: Dict) -> Dict:
    """Полная проверка всех компонентов"""
    results = {}
    
    if "graph" in components:
        results["neo4j"] = await check_neo4j(components["graph"])
    
    if "redis" in components:
        results["redis"] = await check_redis(components["redis"])
    
    # Общий статус
    all_healthy = all(
        r.get("status") == "healthy" 
        for r in results.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": results,
        "timestamp": time.time()
    }

