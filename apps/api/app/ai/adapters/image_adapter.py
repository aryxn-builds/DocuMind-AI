import uuid
import base64

from app.ai.models import NormalizedDocument, DocumentBlock, BlockType
from app.ai.adapters.base import BaseAdapter


class ImageAdapter(BaseAdapter):
    """Adapter for processing standalone image files (PNG/JPEG)."""

    def parse(self, file_bytes: bytes) -> NormalizedDocument:
        block_id = str(uuid.uuid4())
        
        # Convert the bytes to base64 for embedding in the block
        b64_image = base64.b64encode(file_bytes).decode("utf-8")
        image_ref = f"data:{self.mime_type};base64,{b64_image}"

        block = DocumentBlock(
            block_id=block_id,
            block_type=BlockType.IMAGE,
            content="",  # Populated later by vision enrichment
            page_number=1,
            image_ref=image_ref,
        )

        return NormalizedDocument(
            document_id=self.document_id,
            user_id=self.user_id,
            file_path=self.file_path,
            source_mime_type=self.mime_type,
            page_count=1,
            title=self.title,
            blocks=[block],
            processing_metadata={"adapter": "ImageAdapter"}
        )
