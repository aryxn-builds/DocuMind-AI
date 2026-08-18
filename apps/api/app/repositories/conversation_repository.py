"""
DocuMind AI — Conversation Repository.
"""

from __future__ import annotations

import logging
import uuid

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
    document_id: uuid.UUID | None = None
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
    if not getattr(response, "data", None):
        raise RuntimeError("Failed to insert conversation record")

    return getattr(response, "data", [None])[0]

def get_conversation_by_id(conversation_id: uuid.UUID, user_id: str) -> dict | None:
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
    if not response:
        return None
    return getattr(response, "data", []) if hasattr(response, 'data') else response.get('data')

def list_conversations(user_id: str, document_id: str | None = None, limit: int = 50) -> list[dict]:
    """Lists recent conversations for a user."""
    query = _client().table(TABLE).select("*, documents(original_filename)").eq("user_id", user_id)
    
    if document_id:
        query = query.eq("document_id", document_id)
        
    response = (
        query
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return getattr(response, "data", []) or []

def update_conversation_timestamp_and_title(conversation_id: uuid.UUID, user_id: str, title: str | None = None) -> None:
    """Updates the updated_at timestamp, and optionally the title."""
    from datetime import datetime, timezone
    
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if title:
        updates["title"] = title
        
    _client().table(TABLE).update(updates).eq("id", str(conversation_id)).eq("user_id", user_id).execute()
