"""Health router."""

from fastapi import APIRouter
from backend.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    from backend.main import agent
    return {
        "status": "ok",
        "agent": agent.agent_name if agent else None,
        "user": agent.user_name if agent else None,
        "model": agent.config.get("model") if agent else None,
    }

