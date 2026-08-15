from app.ai.adapters.base import BaseAdapter
from app.ai.adapters.docling_adapter import DoclingAdapter
from app.ai.adapters.image_adapter import ImageAdapter


def get_adapter(document_id: str, user_id: str, file_path: str, mime_type: str, title: str) -> BaseAdapter:
    """Returns the appropriate adapter based on MIME type."""
    if mime_type in ["image/png", "image/jpeg", "image/jpg"]:
        return ImageAdapter(document_id, user_id, file_path, mime_type, title)
    elif mime_type in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return DoclingAdapter(document_id, user_id, file_path, mime_type, title)
    else:
        # Fallback to Docling which might support it, or we could raise an error
        return DoclingAdapter(document_id, user_id, file_path, mime_type, title)
