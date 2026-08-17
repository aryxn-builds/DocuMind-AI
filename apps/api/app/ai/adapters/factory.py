from app.ai.adapters.base import BaseAdapter
from app.ai.adapters.docx_adapter import DocxAdapter
from app.ai.adapters.image_adapter import ImageAdapter
from app.ai.adapters.pdf_adapter import PdfAdapter


def get_adapter(
    document_id: str, user_id: str, file_path: str, mime_type: str, title: str
) -> BaseAdapter:
    """Returns the appropriate adapter based on MIME type.

    Adapters are intentionally lightweight — no PyTorch, no ML model downloads.
    This keeps peak RAM well under Render Free's 512 MB limit.
    """
    if mime_type in ["image/png", "image/jpeg", "image/jpg"]:
        return ImageAdapter(document_id, user_id, file_path, mime_type, title)
    elif mime_type == "application/pdf":
        return PdfAdapter(document_id, user_id, file_path, mime_type, title)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return DocxAdapter(document_id, user_id, file_path, mime_type, title)
    else:
        # Fallback to PDF adapter (best-effort)
        return PdfAdapter(document_id, user_id, file_path, mime_type, title)
