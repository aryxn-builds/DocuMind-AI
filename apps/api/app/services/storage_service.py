"""
DocuMind AI — Storage Service.

Wraps all Supabase Storage operations using the service-role admin client.
The service-role key is NEVER exposed to the frontend or returned in any
API response.

Responsibilities:
- Generate signed upload URLs (PUT-only, 10-minute TTL)
- Check whether a Storage object exists at an expected path
- Delete Storage objects (used for rollback and user-initiated delete)

Isolation guarantee: Storage path is always constructed by this service
using backend-supplied user_id and document_id — never from user input.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Signed upload URL TTL in seconds (10 minutes).
SIGNED_URL_TTL_SECONDS: int = 600

STORAGE_BUCKET: str = "documents"


def _get_admin_client() -> Client:
    """
    Returns a Supabase client authenticated with the service role key.
    This client bypasses RLS and must only be used server-side.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def build_storage_path(user_id: str, document_id: str, sanitized_filename: str) -> str:
    """
    Constructs the canonical storage object path.

    Format: {user_id}/{document_id}/{sanitized_filename}

    The first segment is always user_id so Storage RLS can enforce
    per-user isolation with a simple prefix check.
    """
    return f"{user_id}/{document_id}/{sanitized_filename}"


def generate_signed_upload_url(file_path: str) -> tuple[str, datetime]:
    """
    Creates a signed upload URL for the given storage path.

    Returns:
        (signed_url, expires_at_utc)

    The signed URL is PUT-only and expires after SIGNED_URL_TTL_SECONDS.
    It cannot be used for GET (download).

    Raises:
        RuntimeError: if Supabase Storage fails to generate the URL.
    """
    client = _get_admin_client()

    try:
        response = client.storage.from_(STORAGE_BUCKET).create_signed_upload_url(file_path)

        # Supabase Python SDK returns a dict with 'signedURL' key.
        signed_url = response.get("signed_url") or response.get("signedURL") or response.get("signedUrl")
        if not signed_url:
            raise RuntimeError(
                f"Supabase Storage returned no signed URL for path: {file_path}. "
                f"Response: {response}"
            )

        expires_at = datetime.now(UTC) + timedelta(seconds=SIGNED_URL_TTL_SECONDS)
        return signed_url, expires_at

    except Exception as exc:
        logger.error(
            "storage.signed_url_failed",
            extra={"file_path": file_path, "error": str(exc)},
        )
        raise RuntimeError(f"Failed to generate signed upload URL: {exc}") from exc


def object_exists(file_path: str) -> bool:
    """
    Checks whether a Storage object exists at the given path.

    Used after the frontend PUT to verify the upload actually completed
    before creating the processing_jobs record.

    Returns:
        True if the object exists, False otherwise.
    """
    client = _get_admin_client()

    try:
        # list() with a prefix search for the exact file path.
        # We use the parent folder (second path segment) as the prefix and
        # filter by the full filename.
        parts = file_path.split("/")
        if len(parts) < 3:
            return False

        folder_prefix = "/".join(parts[:-1])
        filename = parts[-1]

        result = client.storage.from_(STORAGE_BUCKET).list(
            folder_prefix,
            {"search": filename},
        )

        # result is a list of file metadata dicts.
        return any(obj.get("name") == filename for obj in (result or []))

    except Exception as exc:
        logger.error(
            "storage.object_exists_check_failed",
            extra={"file_path": file_path, "error": str(exc)},
        )
        return False


def delete_object(file_path: str) -> bool:
    """
    Deletes a Storage object at the given path.

    Used in two contexts:
    1. Active rollback: called by the backend when registration fails after
       a successful upload, to prevent orphaned Storage objects.
    2. User-initiated delete: called by DELETE /api/v1/documents/{id}.

    Returns:
        True if deletion succeeded or the object did not exist.
        False if deletion failed (caller should log and surface the error).
    """
    client = _get_admin_client()

    try:
        client.storage.from_(STORAGE_BUCKET).remove([file_path])
        logger.info(
            "storage.object_deleted",
            extra={"file_path": file_path},
        )
        return True

    except Exception as exc:
        logger.error(
            "storage.object_delete_failed",
            extra={"file_path": file_path, "error": str(exc)},
        )
        return False


def download_document(file_path: str) -> bytes:
    """
    Downloads a document from Supabase Storage.
    
    Returns:
        The raw bytes of the file.
        
    Raises:
        RuntimeError: if the download fails.
    """
    client = _get_admin_client()
    try:
        response = client.storage.from_(STORAGE_BUCKET).download(file_path)
        if not response:
            raise RuntimeError("Empty response from Supabase storage download.")
        return response
    except Exception as exc:
        logger.error(
            "storage.download_failed",
            extra={"file_path": file_path, "error": str(exc)},
        )
        raise RuntimeError(f"Failed to download document: {exc}") from exc
