import os
import tempfile

os.environ["TORCHDYNAMO_DISABLE"] = "1"

import logging
import uuid

from app.ai.adapters.base import BaseAdapter
from app.ai.models import BlockType, BoundingBox, DocumentBlock, NormalizedDocument

logger = logging.getLogger(__name__)


class DoclingAdapter(BaseAdapter):
    """Adapter for processing PDFs and DOCX files using Docling."""

    def parse(self, file_bytes: bytes) -> NormalizedDocument:
        suffix = ".pdf" if self.mime_type == "application/pdf" else ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(tmp_path)
            doc = result.document

            blocks: list[DocumentBlock] = []

            # We use iterate_items() to traverse the document in reading order
            for item, level in doc.iterate_items():
                label = getattr(item, "label", "text")

                if label in ["text", "paragraph"]:
                    block_type = BlockType.TEXT
                elif label == "section_header":
                    block_type = BlockType.HEADING
                elif label == "table":
                    block_type = BlockType.TABLE
                elif label == "picture":
                    block_type = BlockType.IMAGE
                elif label == "list_item":
                    block_type = BlockType.LIST
                elif label == "caption":
                    block_type = BlockType.CAPTION
                else:
                    block_type = BlockType.TEXT

                content = getattr(item, "text", "")

                # Extract BoundingBox if available
                bbox = None
                page_number = None
                if hasattr(item, "prov") and item.prov:
                    prov = item.prov[0]
                    if hasattr(prov, "bbox"):
                        bbox_obj = prov.bbox
                        # Docling bboxes have l, t, r, b
                        bbox = BoundingBox(
                            x0=getattr(bbox_obj, "l", 0.0),
                            y0=getattr(bbox_obj, "t", 0.0),
                            x1=getattr(bbox_obj, "r", 0.0),
                            y1=getattr(bbox_obj, "b", 0.0),
                            page_width=getattr(prov, "page_width", 0.0),
                            page_height=getattr(prov, "page_height", 0.0)
                        )
                    page_number = getattr(prov, "page_no", None)

                table_data = None
                if block_type == BlockType.TABLE and hasattr(item, "export_to_dataframe"):
                    try:
                        df = item.export_to_dataframe()
                        # df columns might be multi-index or not cleanly formatted
                        table_data = [df.columns.tolist()] + df.values.tolist()
                        if hasattr(item, "export_to_markdown"):
                            content = item.export_to_markdown()
                    except Exception as e:
                        logger.warning(f"Failed to export table to dataframe: {e}")

                # Note: Docling picture extraction requires specific converter config to yield image bytes.
                # For Phase 8 MVP, we extract the image structure block. Image bytes for PDF images
                # can be deferred to a later enhancement or configured via ImageFormat.
                image_ref = None

                block = DocumentBlock(
                    block_id=str(uuid.uuid4()),
                    block_type=block_type,
                    content=content,
                    page_number=page_number,
                    bbox=bbox,
                    table_data=table_data,
                    image_ref=image_ref,
                )

                if content.strip() or block_type in [BlockType.IMAGE, BlockType.TABLE]:
                    blocks.append(block)

            # Estimate page count
            page_count = len(doc.pages) if hasattr(doc, "pages") else 1

            return NormalizedDocument(
                document_id=self.document_id,
                user_id=self.user_id,
                file_path=self.file_path,
                source_mime_type=self.mime_type,
                page_count=page_count,
                title=self.title,
                blocks=blocks,
                processing_metadata={"adapter": "DoclingAdapter"}
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
