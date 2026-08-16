"""
DocuMind AI — Document Service.

Handles business logic for document uploads, registration, listing, and deletion.
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import BackgroundTasks, HTTPException, status

from app.ai.processing_orchestrator import ProcessingOrchestrator
from app.repositories import document_repository, job_repository
from app.schemas.document import (
    ALLOWED_MIME_TYPES,
    DocumentListResponse,
    DocumentRegisterRequest,
    DocumentRegisterResponse,
    DocumentResponse,
    DocumentStatusResponse,
    SignedUrlRequest,
    SignedUrlResponse,
)
from app.services import storage_service

logger = logging.getLogger(__name__)

# Single instance of orchestrator for background tasks
orchestrator = ProcessingOrchestrator()

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes the filename to prevent path traversal and remove unsafe characters.
    Allows alphanumeric, underscores, hyphens, and dots.
    """
    # Remove path components
    filename = filename.replace("\\", "/").split("/")[-1]

    # Replace spaces with underscores
    filename = re.sub(r"\s+", "_", filename)

    # Keep only safe characters
    filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "", filename)

    if not filename:
        filename = "document"

    return filename


def get_upload_url(user_id: str, request: SignedUrlRequest) -> SignedUrlResponse:
    """
    Validates the file request, generates a signed upload URL,
    and inserts a 'pending' document record into the database.
    """
    # Validate extension and MIME type
    extension = "." + request.filename.split('.')[-1].lower() if '.' in request.filename else ""
    if extension not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension}",
        )

    if ALLOWED_MIME_TYPES[extension] != request.file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{request.file_type}' does not match extension '{extension}'. Expected '{ALLOWED_MIME_TYPES[extension]}'."
        )

    document_id = uuid.uuid4()
    sanitized_filename = sanitize_filename(request.filename)

    # Build the strict storage path
    file_path = storage_service.build_storage_path(
        user_id=user_id,
        document_id=str(document_id),
        sanitized_filename=sanitized_filename,
    )

    try:
        signed_url, expires_at = storage_service.generate_signed_upload_url(file_path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate upload URL.",
        ) from exc

    try:
        document_repository.insert_document(
            document_id=document_id,
            user_id=user_id,
            title=request.filename,
            original_filename=request.filename,
            file_path=file_path,
            file_type=request.file_type,
            file_size_bytes=request.file_size_bytes,
            status="pending",
        )
    except Exception as exc:
        logger.error(f"Failed to insert pending document: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize document upload.",
        ) from exc

    return SignedUrlResponse(
        document_id=document_id,
        signed_url=signed_url,
        file_path=file_path,
        expires_at=expires_at,
    )

def get_document_status(user_id: str, document_id: uuid.UUID) -> DocumentStatusResponse:
    """Retrieves lightweight processing status and progress."""
    doc = document_repository.get_document_by_id(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    job = job_repository.get_job_by_document(document_id, user_id)
    progress = 0.0
    error_details = None

    if job:
        progress = job.get("progress") or 0.0
        error_details = job.get("error_details")

    return DocumentStatusResponse(
        status=doc["status"],
        progress=progress,
        error_details=error_details
    )

# ...

def register_document(
    user_id: str,
    request: DocumentRegisterRequest,
    background_tasks: BackgroundTasks
) -> DocumentRegisterResponse:
    """
    Called after the client successfully uploads to Storage.
    Verifies the file exists, updates status, and queues processing.
    """
    # Verify the document exists and belongs to the user
    doc = document_repository.get_document_by_id(request.document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not pending (status: {doc['status']}).",
        )

    # Validate that the file path matches
    if doc["file_path"] != request.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path mismatch.",
        )

    # Check if the object actually exists in Supabase Storage
    if not storage_service.object_exists(request.file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in storage. The upload may not have completed.",
        )

    # Advance document status
    updated_doc = document_repository.update_document_status(
        document_id=request.document_id,
        user_id=user_id,
        status="queued"
    )
    if not updated_doc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document status.",
        )

    # Create the processing job
    try:
        job = job_repository.insert_job(
            document_id=request.document_id,
            user_id=user_id,
            job_type="ingestion",
            status="queued"
        )
    except Exception as exc:
        logger.error(f"Failed to create processing job: {exc}")
        document_repository.update_document_status(
            document_id=request.document_id,
            user_id=user_id,
            status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document was registered but failed to queue for processing.",
        ) from exc

    # Dispatch to background tasks
    background_tasks.add_task(orchestrator.run, job["id"], str(request.document_id), user_id)

    return DocumentRegisterResponse(
        id=request.document_id,
        status="queued",
        job_id=uuid.UUID(job["id"]),
    )


def list_documents(
    user_id: str,
    status_filter: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> DocumentListResponse:
    """Lists documents with pagination."""
    docs_data = document_repository.list_documents(
        user_id=user_id,
        status_filter=status_filter,
        limit=limit,
        cursor=cursor,
    )

    next_cursor = None
    if len(docs_data) > limit:
        next_cursor = docs_data[limit]["created_at"]
        docs_data = docs_data[:limit]

    # Convert to Pydantic models
    documents = [DocumentResponse.model_validate(doc) for doc in docs_data]

    # TODO: 'total' is required by response model but repository does not return it.
    # Return count of this page for now.
    return DocumentListResponse(
        documents=documents,
        next_cursor=next_cursor,
        total=len(documents)
    )


def get_document(user_id: str, document_id: uuid.UUID) -> DocumentResponse:
    """Retrieves a single document."""
    doc = document_repository.get_document_by_id(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return DocumentResponse.model_validate(doc)


def delete_document(user_id: str, document_id: uuid.UUID) -> None:
    """
    Deletes a document from the database and storage.
    E. Delete document -> remove database record and associated Storage object safely.
    """
    doc = document_repository.get_document_by_id(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Delete from storage first
    # If storage deletion fails, we don't delete the DB record to avoid orphaned files.
    if not storage_service.delete_object(doc["file_path"]):
        # It's possible the object was already deleted, but storage_service handles that gracefully.
        # If it returns False, it's a real failure.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from storage.",
        )

    # Delete from database
    if not document_repository.delete_document(document_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document record.",
        )
