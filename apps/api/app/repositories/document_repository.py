"""
DocuMind AI — Document Repository.

All database queries against the `documents` table are here.
Every query filters by user_id (from JWT sub) — RLS is a second layer,
not the primary ownership enforcement mechanism.
"""

from __future__ import annotations

import logging
import uuid

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

TABLE = "documents"


def _client() -> Client:
    """Returns a Supabase client using the service-role key for DB access."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def insert_document(
    *,
    document_id: uuid.UUID,
    user_id: str,
    title: str,
    original_filename: str,
    file_path: str,
    file_type: str,
    file_size_bytes: int,
    status: str = "pending",
) -> dict:
    """
    Inserts a new document record.
    Called by the signed-url endpoint before generating the upload URL.
    """
    record = {
        "id": str(document_id),
        "user_id": user_id,
        "title": title,
        "original_filename": original_filename,
        "file_path": file_path,
        "file_type": file_type,
        "file_size_bytes": file_size_bytes,
        "status": status,
    }

    response = _client().table(TABLE).insert(record).execute()

    if not response.data:
        raise RuntimeError(f"Failed to insert document record: {response}")

    logger.info(
        "document.inserted",
        extra={
            "user_id": user_id,
            "document_id": str(document_id),
            "file_type": file_type,
            "file_size_bytes": file_size_bytes,
        },
    )
    return response.data[0]


def get_document_by_id(document_id: uuid.UUID, user_id: str) -> dict | None:
    """
    Fetches a document by ID, filtered strictly by user_id.
    Returns None if not found or not owned by this user (caller returns 404).
    """
    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("id", str(document_id))
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return response.data


def update_document_status(
    document_id: uuid.UUID,
    user_id: str,
    status: str,
) -> dict | None:
    """Updates the status column of a document."""
    response = (
        _client()
        .table(TABLE)
        .update({"status": status})
        .eq("id", str(document_id))
        .eq("user_id", user_id)
        .execute()
    )
    return response.data[0] if response.data else None


def list_documents(
    user_id: str,
    status_filter: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> list[dict]:
    """
    Lists documents for a user, ordered by created_at DESC.
    Supports cursor-based pagination via document UUID.
    """
    query = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit + 1)  # Fetch one extra to detect next page.
    )

    if status_filter:
        query = query.eq("status", status_filter)

    if cursor:
        # Cursor is the `created_at` timestamp of the last item in the previous page.
        query = query.lt("created_at", cursor)

    response = query.execute()
    return response.data or []


def delete_document(document_id: uuid.UUID, user_id: str) -> bool:
    """
    Deletes the document record. Caller must have already deleted the
    Storage object before calling this.

    Returns True if a record was deleted, False otherwise.
    """
    response = (
        _client()
        .table(TABLE)
        .delete()
        .eq("id", str(document_id))
        .eq("user_id", user_id)
        .execute()
    )
    deleted = bool(response.data)
    if deleted:
        logger.info(
            "document.deleted_from_db",
            extra={"user_id": user_id, "document_id": str(document_id)},
        )
    return deleted
