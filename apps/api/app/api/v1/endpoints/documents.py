"""
DocuMind AI — Documents Endpoints.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.security import get_current_user
from app.repositories import document_repository, job_repository
from app.schemas.document import (
    DocumentListResponse,
    DocumentRegisterRequest,
    DocumentRegisterResponse,
    DocumentResponse,
    DocumentStatusResponse,
    SignedUrlRequest,
    SignedUrlResponse,
)
from app.services import document_service

router = APIRouter()


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get processing status of a document",
)
def get_document_status(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
):
    """
    Retrieve lightweight status and progress for a document.
    """
    return document_service.get_document_status(user_id=user_id, document_id=document_id)


@router.get(
    "/{document_id}/debug-status",
    summary="[DEBUG] Full processing state for a document",
    description=(
        "Returns the complete processing state: document row, job row, and all "
        "timestamps. Use this to diagnose stuck documents in production. "
        "Authenticated owner access only."
    ),
)
def get_document_debug_status(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
):
    """
    Returns full job + document state for production debugging.
    Only the document owner can access this endpoint.
    """
    doc = document_repository.get_document_by_id(document_id, user_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found.")

    job = job_repository.get_job_by_document(document_id, user_id)

    return {
        "document_id": str(document_id),
        "document_status": doc.get("status"),
        "document_created_at": doc.get("created_at"),
        "document_title": doc.get("title"),
        "document_file_type": doc.get("file_type"),
        "document_file_path": doc.get("file_path"),
        "job_id": job.get("id") if job else None,
        "job_status": job.get("status") if job else None,
        "job_created_at": job.get("created_at") if job else None,
        "job_started_at": job.get("started_at") if job else None,
        "job_completed_at": job.get("completed_at") if job else None,
        "job_progress": job.get("progress") if job else None,
        "job_error": job.get("error_details") if job else None,
    }


@router.post(
    "/signed-url",
    response_model=SignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a signed URL for document upload",
)
def get_signed_url(
    request: SignedUrlRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Request a PUT-only signed URL to upload a document directly to Supabase Storage.
    The response includes the `file_path` you must use when uploading, as well as the
    `document_id` to use during the registration step.
    """
    return document_service.get_upload_url(user_id=user_id, request=request)


@router.post(
    "/register",
    response_model=DocumentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a successfully uploaded document",
)
async def register_document(
    request: DocumentRegisterRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """
    Called after the client has successfully uploaded the file to the signed URL.
    This endpoint verifies the upload and queues the processing job.

    The processing job runs as a sync background task (via Starlette's
    anyio thread pool), not as an async coroutine. This is intentional —
    it is more reliable on Render's free tier where async coroutines
    can be silently dropped if the process lifecycle ends between the
    HTTP response and the task completion.
    """
    return document_service.register_document(
        user_id=user_id, request=request, background_tasks=background_tasks
    )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
)
def list_documents(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    user_id: str = Depends(get_current_user),
):
    """
    Retrieve a paginated list of documents.
    """
    return document_service.list_documents(
        user_id=user_id,
        status_filter=status_filter,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a specific document",
)
def get_document(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
):
    """
    Retrieve a single document by its ID.
    """
    return document_service.get_document(user_id=user_id, document_id=document_id)

@router.get(
    "/{document_id}/download-url",
    response_model=dict,
    summary="Get a signed URL for downloading/viewing a document",
)
def get_download_url(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
):
    """
    Request a GET-only signed URL to view a document directly from Supabase Storage.
    """
    url = document_service.get_download_url(user_id=user_id, document_id=document_id)
    return {"url": url}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
def delete_document(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
):
    """
    Delete a document and its associated storage object.
    """
    document_service.delete_document(user_id=user_id, document_id=document_id)
