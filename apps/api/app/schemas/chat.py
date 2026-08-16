"""
DocuMind AI — Pydantic schemas for Chat and RAG endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ===========================================================================
# Citations
# ===========================================================================
class CitationResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    page_number: int | None = None
    excerpt: str
    relevance_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Messages
# ===========================================================================
class MessageCreate(BaseModel):
    role: str = Field(..., description="Role of the sender: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, description="Message content")

class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    tokens_used: int | None = None
    provider: str | None = None
    model: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Conversations
# ===========================================================================
class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    document_id: uuid.UUID | None = Field(
        default=None,
        description="If provided, this conversation is scoped to a specific document."
    )

class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    document_id: uuid.UUID | None = None
    messages: list[MessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Search
# ===========================================================================
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    document_id: uuid.UUID | None = Field(default=None, description="Optional document filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_type: str
    page_number: int | None = None
    content: str
    relevance_score: float

class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_time_ms: float


# ===========================================================================
# RAG (Retrieval-Augmented Generation)
# ===========================================================================
class RagRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question")
    document_id: uuid.UUID | None = Field(default=None, description="Optional document filter for single-doc chat")

class RagResponse(BaseModel):
    """
    If using SSE streaming, this model might not be returned directly,
    but could represent the final accumulated state or a non-streaming fallback.
    """
    message: MessageResponse
