"""
DocuMind AI — Citation Repository.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, List

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

TABLE = "citations"

def _client() -> Client:
    """Returns a Supabase client using the service-role key for DB access."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

def create_citations(
    user_id: str,
    citations_data: List[dict]
) -> List[dict]:
    """
    Bulk inserts citations. 
    citations_data should include: message_id, document_id, chunk_id, page_number, excerpt, relevance_score.
    """
    if not citations_data:
        return []

    records = []
    for data in citations_data:
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "message_id": str(data["message_id"]),
            "document_id": str(data["document_id"]),
            "chunk_id": str(data["chunk_id"]),
            "page_number": data.get("page_number"),
            "excerpt": data.get("excerpt", ""),
            "relevance_score": data.get("relevance_score", 0.0)
        }
        records.append(record)
        
    response = _client().table(TABLE).insert(records).execute()
    return response.data or []

def get_citations_for_message(message_id: uuid.UUID, user_id: str) -> List[dict]:
    """Gets citations for a specific message, filtered by user_id."""
    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("message_id", str(message_id))
        .eq("user_id", user_id)
        .execute()
    )
    return response.data or []
