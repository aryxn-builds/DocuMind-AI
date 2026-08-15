"""
DocuMind AI — Processing Job Repository.

All database queries against the `processing_jobs` table.
Every query is scoped by user_id (from JWT).
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

TABLE = "processing_jobs"


def _client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def insert_job(
    *,
    document_id: uuid.UUID,
    user_id: str,
    job_type: str = "ingestion",
    status: str = "queued",
) -> dict:
    """
    Inserts a new processing job record.
    Called after the document record has been advanced to 'queued'.
    user_id is always sourced from the JWT sub claim.
    """
    record = {
        "id": str(uuid.uuid4()),
        "document_id": str(document_id),
        "user_id": user_id,
        "job_type": job_type,
        "status": status,
    }

    response = _client().table(TABLE).insert(record).execute()

    if not response.data:
        raise RuntimeError(f"Failed to insert processing_job record: {response}")

    logger.info(
        "job.inserted",
        extra={
            "user_id": user_id,
            "document_id": str(document_id),
            "job_id": record["id"],
        },
    )
    return response.data[0]


def get_job_by_document(document_id: uuid.UUID, user_id: str) -> Optional[dict]:
    """Returns the most recent job for a given document."""
    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("document_id", str(document_id))
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
