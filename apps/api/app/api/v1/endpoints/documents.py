"""
DocuMind AI — Documents Endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status, BackgroundTasks

from app.core.security import get_current_user
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
def register_document(
    request: DocumentRegisterRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """
    Called after the client has successfully uploaded the file to the signed URL.
    This endpoint verifies the upload and queues the processing job.
    """
    return document_service.register_document(user_id=user_id, request=request, background_tasks=background_tasks)


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
