"""
DocuMind AI — Pydantic schemas for Document and Upload endpoints.

Multi-model pattern:
  - *Base: shared fields
  - *Create / *Request: inbound payloads
  - *Response: outbound payloads
  - *Status: lightweight polling response
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Constants (mirrors DATABASE_SCHEMA.md §3.2 and §3.9 status enums)
# ---------------------------------------------------------------------------
ALLOWED_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

DOCUMENT_STATUS_VALUES = frozenset({"pending", "queued", "processing", "ready", "failed"})
JOB_STATUS_VALUES = frozenset({"queued", "processing", "completed", "failed"})

MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB


# ===========================================================================
# Upload — Step 1: Request a signed upload URL
# ===========================================================================
class SignedUrlRequest(BaseModel):
    """
    Payload sent by the frontend to obtain a signed upload URL.
    user_id is NOT present here — it is always extracted from the JWT.
    """

    filename: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Original filename provided by the user.",
    )
    file_type: str = Field(
        ...,
        description="MIME type of the file (e.g., 'application/pdf').",
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        description="File size in bytes. Must be > 0 and ≤ 25 MB.",
    )

    @field_validator("file_size_bytes")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {v} bytes exceeds maximum allowed size of "
                f"{MAX_FILE_SIZE_BYTES} bytes (25 MB)."
            )
        return v


class SignedUrlResponse(BaseModel):
    """Returned to the frontend after validation passes."""

    document_id: uuid.UUID
    signed_url: str = Field(description="PUT-only signed URL for Supabase Storage upload.")
    file_path: str = Field(description="The exact Storage object path the frontend must PUT to.")
    expires_at: datetime = Field(description="When the signed URL expires (UTC).")


# ===========================================================================
# Upload — Step 2: Register a completed upload
# ===========================================================================
class DocumentRegisterRequest(BaseModel):
    """
    Sent by the frontend after the PUT to Supabase Storage completes.
    user_id is NOT included — always extracted from JWT sub.
    """

    document_id: uuid.UUID = Field(description="UUID issued by the signed-url endpoint.")
    file_path: str = Field(
        ...,
        min_length=1,
        description="The Storage object path returned by signed-url endpoint.",
    )
    original_filename: str = Field(..., min_length=1, max_length=500)
    file_type: str = Field(...)
    file_size_bytes: int = Field(..., gt=0)
    title: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional display title. Defaults to original_filename.",
    )


class DocumentRegisterResponse(BaseModel):
    """Returned after successful registration and job creation."""

    id: uuid.UUID
    status: str
    job_id: uuid.UUID


# ===========================================================================
# Document — Response models
# ===========================================================================
class DocumentResponse(BaseModel):
    """Full document object returned to the frontend."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    status: str
    page_count: Optional[int] = None
    processing_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    """Lightweight polling response for status checks."""

    status: str
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    error_details: Optional[dict] = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: list[DocumentResponse]
    next_cursor: Optional[str] = None
    total: int


# ===========================================================================
# Processing Job — Response model
# ===========================================================================
class ProcessingJobResponse(BaseModel):
    """Processing job details."""

    id: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID
    job_type: str
    status: str
    progress: Optional[float] = None
    error_details: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
