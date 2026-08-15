"""
DocuMind AI — Message Repository.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, List

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

TABLE = "messages"

def _client() -> Client:
    """Returns a Supabase client using the service-role key for DB access."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

def create_message(
    *,
    user_id: str,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    tokens_used: Optional[int] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> dict:
    """Creates a new message in a conversation. Enforces user_id ownership."""
    message_id = str(uuid.uuid4())
    record = {
        "id": message_id,
        "conversation_id": str(conversation_id),
        "user_id": user_id,
        "role": role,
        "content": content,
        "tokens_used": tokens_used,
        "provider": provider,
        "model": model
    }
    
    response = _client().table(TABLE).insert(record).execute()
    if not response.data:
        raise RuntimeError("Failed to insert message record")
        
    return response.data[0]

def list_messages_for_conversation(conversation_id: uuid.UUID, user_id: str) -> List[dict]:
    """Lists all messages for a conversation, ordered chronologically, filtered by user_id."""
    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return response.data or []
