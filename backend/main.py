"""
FastAPI backend для Fractal Memory.

Единственный event loop — все async операции здесь.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import get_settings
from backend.routers import chat, memory, health
from src.agent import FractalAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальный агент (singleton)
agent: Optional[FractalAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup и shutdown."""
    global agent
    
    # === STARTUP ===
    settings = get_settings()
    
    # Безопасность: проверка пароля
    if not settings.neo4j_password or settings.neo4j_password in ["", "changeme", "password", "changeme_secure_password_123"]:
        logger.warning(
            "⚠️  SECURITY WARNING: NEO4J_PASSWORD is not set or uses insecure default. "
            "Set NEO4J_PASSWORD environment variable!"
        )
        if not settings.neo4j_password:
            raise ValueError(
                "NEO4J_PASSWORD environment variable is required. "
                "Set it in .env file or environment."
            )
    
    config = {
        "neo4j_uri": settings.neo4j_uri,
        "neo4j_user": settings.neo4j_user,
        "neo4j_password": settings.neo4j_password,
        "redis_url": settings.redis_url,
        "openai_api_key": settings.openai_api_key,
        "model": settings.llm_model,
        "user_id": settings.user_id,
        "user_name": settings.user_name,
        "agent_name": settings.agent_name,
        "consolidation_threshold": settings.consolidation_threshold,
        "l0_max_size": settings.l0_max_size,
    }
    
    agent = FractalAgent(config)
    await agent.initialize()
    
    logger.info(f"🚀 Agent started: {settings.agent_name} for {settings.user_name}")
    logger.info(f"📦 Model: {settings.llm_model}")
    
    yield
    
    # === SHUTDOWN ===
    if agent:
        await agent.close()
    logger.info("Agent stopped")


app = FastAPI(
    title="Fractal Memory API",
    version="2.0.0",
    description="AI Agent with hierarchical memory",
    lifespan=lifespan,
)

from backend.config import get_settings
from backend.routers import chat, memory, health
from src.agent import FractalAgent
from fastapi import Depends


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Подключение роутеров ====================

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(memory.router)


# ==================== Дополнительные endpoints ====================

@app.get("/strategies")
async def get_strategies(task_type: str = None):
    """Получить стратегии."""
    if agent is None:
        raise HTTPException(503, "Agent not initialized")
    if not hasattr(agent, "reasoning") or not agent.reasoning:
        return {"strategies": []}
    strategies = await agent.reasoning.get_strategies(
        task_type=task_type or "general",
        limit=10,
    )
    return {
        "strategies": [
            {
                "id": s.id,
                "task_type": s.task_type,
                "description": s.description,
                "success_rate": s.success_rate,
                "usage_count": s.usage_count,
            }
            for s in strategies
        ]
    }


# ==================== Run ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

