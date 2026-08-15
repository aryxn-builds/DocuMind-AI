"""
DocuMind AI — Conversation Repository.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, List

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

TABLE = "conversations"

def _client() -> Client:
    """Returns a Supabase client using the service-role key for DB access."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

def create_conversation(
    *,
    user_id: str,
    title: str = "New Conversation",
    document_id: Optional[uuid.UUID] = None
) -> dict:
    """Creates a new conversation for the user."""
    conversation_id = str(uuid.uuid4())
    record = {
        "id": conversation_id,
        "user_id": user_id,
        "title": title,
        "document_id": str(document_id) if document_id else None
    }
    
    response = _client().table(TABLE).insert(record).execute()
    if not response.data:
        raise RuntimeError("Failed to insert conversation record")
        
    return response.data[0]

def get_conversation_by_id(conversation_id: uuid.UUID, user_id: str) -> Optional[dict]:
    """Fetches a conversation by ID, strictly filtered by user_id."""
    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("id", str(conversation_id))
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return response.data

def list_conversations(user_id: str, limit: int = 20) -> List[dict]:
    """Lists recent conversations for a user."""
    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []
