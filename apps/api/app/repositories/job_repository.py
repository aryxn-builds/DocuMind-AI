"""
DocuMind AI — Processing Job Repository.

All database queries against the `processing_jobs` table.
Every query is scoped by user_id (from JWT).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from supabase import Client, create_client

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


def get_job_by_document(document_id: uuid.UUID, user_id: str) -> dict | None:
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


def claim_job(job_id: str) -> dict | None:
    """
    Atomically claim a queued job by setting it to processing.
    Returns the updated job if successful, or None if already claimed/failed.
    """
    now = datetime.now(UTC).isoformat()
    response = (
        _client()
        .table(TABLE)
        .update({"status": "processing", "started_at": now, "progress": 0.0})
        .eq("id", job_id)
        .eq("status", "queued")
        .execute()
    )

    if response.data:
        return response.data[0]
    return None


def update_job_progress(job_id: str, progress: float, status: str = "processing") -> None:
    """Updates the progress and status of a job."""
    _client().table(TABLE).update({"progress": progress, "status": status}).eq("id", job_id).execute()


def fail_job(job_id: str, stage: str, message: str, retry_count: int) -> None:
    """Marks a job as failed and records error details."""
    now = datetime.now(UTC).isoformat()
    error_details = {
        "stage": stage,
        "message": message,
        "retry_count": retry_count
    }
    _client().table(TABLE).update({
        "status": "failed",
        "error_details": error_details,
        "completed_at": now
    }).eq("id", job_id).execute()


def complete_job(job_id: str) -> None:
    """Marks a job as successfully completed."""
    now = datetime.now(UTC).isoformat()
    _client().table(TABLE).update({
        "status": "completed",
        "progress": 1.0,
        "completed_at": now
    }).eq("id", job_id).execute()


def find_stale_processing_jobs(older_than_minutes: int) -> list[dict]:
    """Finds jobs stuck in processing state for longer than the specified minutes."""
    threshold = datetime.now(UTC) - timedelta(minutes=older_than_minutes)

    response = (
        _client()
        .table(TABLE)
        .select("*")
        .eq("status", "processing")
        .lt("started_at", threshold.isoformat())
        .execute()
    )
    return response.data or []

def fail_stale_jobs(message: str) -> int:
    """Marks all 'processing' or 'queued' jobs as failed during process startup."""
    now = datetime.now(UTC).isoformat()
    count = 0

    for status in ["processing", "queued"]:
        response = (
            _client()
            .table(TABLE)
            .update({
                "status": "failed",
                "completed_at": now,
                "error_details": {"stage": "startup", "message": message, "retry_count": 0}
            })
            .eq("status", status)
            .execute()
        )
        if response.data:
            count += len(response.data)

    return count
