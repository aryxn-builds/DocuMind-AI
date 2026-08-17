import logging

from supabase import Client, create_client

from app.ai.models import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)

TABLE = "document_chunks"

def _client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

def insert_chunks(chunks: list[Chunk]):
    if not chunks:
        return

    records = []
    for chunk in chunks:
        records.append({
            "id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "user_id": chunk.user_id,
            "chunk_index": chunk.chunk_index,
            "content_preview": chunk.content_preview,
            "chunk_type": chunk.chunk_type,
            "page_number": chunk.page_number,
            "qdrant_point_id": chunk.chunk_id,
            "position_metadata": {
                "section_path": chunk.section_path,
                "bbox": chunk.bbox.__dict__ if chunk.bbox else None,
                "table_data": chunk.table_data,
            }
        })

    try:
        # In production, we'd batch these for very large documents.
        # For Phase 8 MVP, we do it in one shot.
        _client().table(TABLE).insert(records).execute()
    except Exception as e:
        logger.error(f"Failed to insert chunks into {TABLE}: {e}")
        raise

def delete_by_document(document_id: str, user_id: str):
    """
    Deletes all chunk metadata for a document. 
    user_id is required to enforce isolation.
    """
    if not user_id:
        raise ValueError("user_id is required for chunk deletion.")

    try:
        _client().table(TABLE).delete().eq("document_id", document_id).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to delete chunks for document {document_id}: {e}")
        raise

def get_chunks_by_ids(chunk_ids: list[str], user_id: str) -> list[dict]:
    """
    Fetches chunks by their IDs, enforcing user ownership.
    """
    if not chunk_ids:
        return []

    response = (
        _client()
        .table(TABLE)
        .select("*")
        .in_("id", chunk_ids)
        .eq("user_id", user_id)
        .execute()
    )
    return getattr(response, "data", []) or []
