"""Memory router."""

from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.agent import FractalAgent
from backend.models import (
    MemoryStats,
    SearchResponse,
    SearchResultItem,
    MemoryNode,
    RememberResponse,
    ConsolidateResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


def get_agent_from_main():
    """Получить агента из main модуля."""
    from backend.main import agent
    if agent is None:
        raise HTTPException(503, "Agent not initialized")
    return agent


@router.get("/stats", response_model=MemoryStats)
async def get_stats(agent: FractalAgent = Depends(get_agent_from_main)):
    """
    Статистика памяти.
    
    Возвращает формат, ожидаемый фронтендом:
    {
      "l0_count": int,
      "l1_count": int,
      "l2_count": int,
      "l3_count": int,
      "last_consolidation": str (ISO datetime)
    }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    stats = await agent.get_stats()
    memory_stats = stats.get("memory", {})
    
    # Получаем реальные значения из Redis для L0/L1
    l0_count = 0
    l1_count = 0
    
    try:
        if hasattr(agent.memory, 'redis_store'):
            # Получаем реальное количество элементов в L0
            l0_items = await agent.memory.redis_store.l0_get_recent(1000)  # Большой лимит для подсчета
            l0_count = len(l0_items)
            
            # Получаем количество сессий/саммарей в L1
            l1_sessions = await agent.memory.redis_store.l1_get_sessions()
            l1_summaries = await agent.memory.redis_store.l1_get_recent_summaries(100)
            l1_count = len(l1_sessions) if l1_sessions else 0
            # fallback: если нет hset-сессий, берём длину списка саммарей
            if l1_count == 0 and l1_summaries:
                l1_count = len(l1_summaries)
            
            logger.info(f"Memory stats: L0={l0_count}, L1={l1_count} (from Redis)")
    except Exception as e:
        logger.warning(f"Failed to get L0/L1 counts from Redis: {e}")
        # Fallback на значения из stats
        l0_count = memory_stats.get("l0_size", memory_stats.get("l0_count", 0))
        l1_count = memory_stats.get("l1_size", memory_stats.get("l1_count", 0))
    
    # Маппинг: бэкенд возвращает l0_size/l1_size, фронтенд ждет l0_count/l1_count
    return {
        "l0_count": l0_count,
        "l1_count": l1_count,
        "l2_count": memory_stats.get("l2_count", 0),
        "l3_count": memory_stats.get("l3_count", 0),
        "last_consolidation": memory_stats.get("last_consolidation") or stats.get("last_consolidation"),
    }


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, agent: FractalAgent = Depends(get_agent_from_main)):
    """Поиск по памяти."""
    results = await agent.retriever.search(request.query, request.limit)
    return {
        "results": [
            {
                "content": r.content,
                "score": r.score,
                "source": r.source,
                "metadata": r.metadata,
            }
            for r in results
        ]
    }


@router.get("/{level}", response_model=List[MemoryNode])
async def get_memory_level(
    level: str, 
    limit: int = 50, 
    agent: FractalAgent = Depends(get_agent_from_main)
):
    """
    Получить узлы памяти для визуализации графа.
    
    Возвращает формат MemoryNode[] для фронтенда:
    [
      {
        "id": str,
        "label": str,
        "content": str,
        "level": "l0" | "l1" | "l2" | "l3",
        "importance": float,
        "created_at": str (ISO datetime),
        "connections": [str] (IDs связанных узлов)
      },
      ...
    ]
    """
    nodes = []
    
    if level == "all":
        # Собираем узлы со всех уровней
        for lvl in ["l0", "l1", "l2", "l3"]:
            level_nodes = await _get_level_nodes(agent, lvl, limit)
            nodes.extend(level_nodes)
    elif level in ["l0", "l1", "l2", "l3"]:
        nodes = await _get_level_nodes(agent, level, limit)
    else:
        raise HTTPException(400, f"Unknown level: {level}. Use 'all', 'l0', 'l1', 'l2', or 'l3'")
    
    return nodes


async def _get_level_nodes(agent: FractalAgent, level: str, limit: int) -> list:
    """Вспомогательная функция для получения узлов уровня."""
    nodes = []
    
    if level == "l0":
        if hasattr(agent.memory, 'redis_store'):
            items = await agent.memory.redis_store.l0_get_recent(limit)
            for idx, item in enumerate(items):
                # item может быть словарем или объектом
                if isinstance(item, dict):
                    content = item.get("content", "")
                    timestamp = item.get("timestamp", "")
                else:
                    # Если это объект с атрибутами
                    content = getattr(item, "content", "")
                    timestamp = getattr(item, "timestamp", "")
                
                # Генерируем ID если его нет
                item_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
                if not item_id:
                    item_id = f"l0_{idx}_{hash(content) % 10000}"
                
                # Форматируем timestamp
                if hasattr(timestamp, "isoformat"):
                    created_at_str = timestamp.isoformat()
                elif isinstance(timestamp, str):
                    created_at_str = timestamp
                else:
                    created_at_str = str(timestamp) if timestamp else ""
                
                nodes.append({
                    "id": str(item_id),
                    "label": content[:50] + "..." if len(content) > 50 else content,
                    "content": content,
                    "level": "l0",
                    "importance": item.get("importance", 0.5) if isinstance(item, dict) else getattr(item, "importance", 0.5),
                    "created_at": created_at_str,
                    "connections": [],  # L0 не имеет связей
                })
    
    elif level == "l1":
        if hasattr(agent.memory, 'redis_store'):
            sessions = await agent.memory.redis_store.l1_get_sessions()
            # sessions может быть списком или словарем
            if isinstance(sessions, list):
                sessions_list = sessions[:limit]
            elif isinstance(sessions, dict):
                sessions_list = list(sessions.items())[:limit]
            else:
                sessions_list = []
            
            for idx, session_item in enumerate(sessions_list):
                if isinstance(session_item, tuple):
                    # Если это (key, value) из dict.items()
                    session_id, session_data = session_item
                elif isinstance(session_item, dict):
                    # Если это список словарей
                    session_id = session_item.get("session_id", f"l1_{idx}")
                    session_data = session_item
                else:
                    continue
                
                # Извлекаем данные
                if isinstance(session_data, dict):
                    summary = session_data.get("summary", "")
                    importance = session_data.get("importance", 0.5)
                    created_at = session_data.get("created_at", "")
                else:
                    summary = str(session_data)[:200]
                    importance = 0.5
                    created_at = ""
                
                # Форматируем created_at
                if hasattr(created_at, "isoformat"):
                    created_at_str = created_at.isoformat()
                elif isinstance(created_at, str):
                    created_at_str = created_at
                else:
                    created_at_str = str(created_at) if created_at else ""
                
                nodes.append({
                    "id": str(session_id),
                    "label": f"Session {str(session_id)[:8]}",
                    "content": summary[:200],
                    "level": "l1",
                    "importance": importance,
                    "created_at": created_at_str,
                    "connections": [],  # L1 связи можно добавить позже
                })
    
    elif level in ["l2", "l3"]:
        # L2/L3 хранятся в Neo4j через GraphitiStore
        if agent.memory and getattr(agent.memory, "graphiti", None):
            try:
                # Для L2 ищем Episodic узлы, для L3 - Entity узлы
                node_label = "Episodic" if level == "l2" else "Entity"
                
                results = await agent.memory.graphiti.execute_cypher(
                    f"""
                    MATCH (n:{node_label})
                    WHERE n.content CONTAINS $user_tag
                    RETURN n.uuid as id,
                           n.content as content,
                           n.created_at as created_at,
                           n.valid_at as valid_at
                    ORDER BY n.created_at DESC
                    LIMIT $limit
                    """,
                    {
                        "user_tag": f"[user:{agent.memory.user_id}]",
                        "limit": limit
                    }
                )
                
                # Получаем связи для каждого узла
                for record in results:
                    node_id = record.get("id")
                    if not node_id:
                        continue
                    
                    # Находим связанные узлы
                    connections_result = await agent.memory.graphiti.execute_cypher(
                        f"""
                        MATCH (n:{node_label} {{uuid: $id}})-[r]-(connected)
                        RETURN connected.uuid as connected_id
                        LIMIT 10
                        """,
                        {"id": node_id}
                    )
                    connections = [r.get("connected_id") for r in connections_result if r.get("connected_id")]
                    
                    content = record.get("content", "")
                    # Убираем user tag из контента для отображения
                    if f"[user:{agent.memory.user_id}]" in content:
                        content = content.replace(f"[user:{agent.memory.user_id}]", "").strip()
                    
                    created_at = record.get("created_at") or record.get("valid_at")
                    if created_at:
                        created_at_str = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
                    else:
                        created_at_str = ""
                    
                    nodes.append({
                        "id": str(node_id),
                        "label": content[:50] + "..." if len(content) > 50 else content,
                        "content": content,
                        "level": level,
                        "importance": 0.7,  # Можно вычислить из других полей
                        "created_at": created_at_str,
                        "connections": [str(c) for c in connections],
                    })
            except Exception as e:
                # Логируем ошибку, но не падаем
                import logging
                logging.getLogger(__name__).warning(f"Failed to get {level} nodes: {e}")
    
    return nodes


class RememberRequest(BaseModel):
    content: str
    importance: float = 0.5


@router.post("/remember", response_model=RememberResponse)
async def remember(
    request: RememberRequest,
    agent: FractalAgent = Depends(get_agent_from_main)
):
    """Сохранить информацию в память."""
    item_id = await agent.memory.remember(
        content=request.content,
        importance=request.importance
    )
    return {
        "status": "ok",
        "item_id": item_id,
        "message": "Content saved to memory"
    }


@router.post("/consolidate", response_model=ConsolidateResponse)
async def consolidate(agent: FractalAgent = Depends(get_agent_from_main)):
    """Запустить консолидацию."""
    result = await agent.memory.consolidate()
    l0_to_l1 = getattr(result, "promoted_l0_to_l1", None)
    l1_to_l2 = getattr(result, "promoted_l1_to_l2", None)
    return {
        "status": "ok",
        "l0_to_l1": l0_to_l1 if l0_to_l1 is not None else getattr(result, "promoted", 0),
        "l1_to_l2": l1_to_l2 if l1_to_l2 is not None else 0,
    }

