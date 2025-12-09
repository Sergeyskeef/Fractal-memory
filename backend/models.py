"""Pydantic models for API responses."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════
# Memory Models
# ═══════════════════════════════════════════════════════

class MemoryStats(BaseModel):
    """Memory statistics response."""
    l0_count: int = Field(..., description="Number of items in L0 (working memory)")
    l1_count: int = Field(..., description="Number of sessions in L1 (short-term)")
    l2_count: int = Field(..., description="Number of episodes in L2 (long-term)")
    l3_count: int = Field(..., description="Number of entities in L3 (semantic)")
    last_consolidation: Optional[str] = Field(None, description="Last consolidation timestamp (ISO format)")


class SearchResultItem(BaseModel):
    """Single search result."""
    content: str = Field(..., description="Content of the result")
    score: float = Field(..., description="Relevance score (0-1)")
    source: str = Field(..., description="Source of the result (l0/l1/l2/l3)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Search results response."""
    results: List[SearchResultItem] = Field(..., description="List of search results")


class MemoryNode(BaseModel):
    """Memory node for graph visualization."""
    id: str = Field(..., description="Unique node ID")
    label: str = Field(..., description="Short label for display")
    content: str = Field(..., description="Full content")
    level: str = Field(..., description="Memory level (l0/l1/l2/l3)")
    importance: float = Field(..., description="Importance score (0-1)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    connections: List[str] = Field(default_factory=list, description="IDs of connected nodes")


class RememberResponse(BaseModel):
    """Response for remember endpoint."""
    status: str = Field(..., description="Status of the operation")
    item_id: str = Field(..., description="ID of the created memory item")
    message: str = Field(..., description="Human-readable message")


class ConsolidateResponse(BaseModel):
    """Response for consolidate endpoint."""
    status: str = Field(..., description="Status of the operation")
    l0_to_l1: int = Field(..., description="Number of items promoted from L0 to L1")
    l1_to_l2: int = Field(..., description="Number of items promoted from L1 to L2")


# ═══════════════════════════════════════════════════════
# Chat Models
# ═══════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    """Chat message for history."""
    id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChatHistoryResponse(BaseModel):
    """Chat history response."""
    messages: List[ChatMessage] = Field(..., description="List of chat messages")


# ═══════════════════════════════════════════════════════
# Health Models
# ═══════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    agent: Optional[str] = Field(None, description="Agent name")
    user: Optional[str] = Field(None, description="User name")
    model: Optional[str] = Field(None, description="LLM model name")
