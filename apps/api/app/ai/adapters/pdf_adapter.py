"""
DocuMind AI — PDF Adapter (PyMuPDF).

Replaces DoclingAdapter for PDF files. Uses PyMuPDF (fitz) — a pure C extension
with no ML dependencies and ~30–50 MB peak RSS, suitable for Render's 512 MB limit.

Tradeoffs vs Docling:
- No deep layout AI (reading-order reconstruction, ML-based table detection)
- Tables are extracted as text rather than structured DataFrames
- Bounding boxes are available natively (Rect objects from fitz)
- Much faster cold start, no model downloads
"""

from __future__ import annotations

import logging
import uuid

from app.ai.adapters.base import BaseAdapter
from app.ai.models import BlockType, BoundingBox, DocumentBlock, NormalizedDocument

logger = logging.getLogger(__name__)


class PdfAdapter(BaseAdapter):
    """Lightweight PDF adapter using PyMuPDF (fitz). No PyTorch, no ML models."""

    # Font-size threshold: blocks whose font size is >= this multiplier of the
    # median body font size are treated as headings.
    HEADING_SCALE_THRESHOLD = 1.15

    def parse(self, file_bytes: bytes) -> NormalizedDocument:
        try:
            import pymupdf as fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError(
                "PyMuPDF (pymupdf) is not installed. Add 'pymupdf>=1.24.0' to requirements.txt."
            ) from exc

        logger.info(f"[PROCESSING] pdf_adapter.parse started document_id={self.document_id}")

        blocks: list[DocumentBlock] = []

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            logger.info(
                f"[PROCESSING] pdf_adapter.opened pages={page_count}"
                f" document_id={self.document_id}"
            )

            # Collect all font sizes across the document to derive a body size baseline.
            all_font_sizes: list[float] = []
            for page in doc:
                for block in page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]:
                    if block["type"] == 0:  # text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                sz = span.get("size", 0)
                                if sz > 0:
                                    all_font_sizes.append(sz)

            # Median font size as the body baseline.
            if all_font_sizes:
                all_font_sizes.sort()
                mid = len(all_font_sizes) // 2
                median_font_size = all_font_sizes[mid]
            else:
                median_font_size = 12.0

            heading_threshold = median_font_size * self.HEADING_SCALE_THRESHOLD

            for page_num, page in enumerate(doc, start=1):
                page_rect = page.rect  # page dimensions for bbox normalisation
                page_w = page_rect.width or 1.0
                page_h = page_rect.height or 1.0

                raw_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

                for raw_block in raw_blocks:
                    btype = raw_block.get("type", 0)

                    if btype == 1:
                        # Image block — record as IMAGE stub (vision enrichment may fill content)
                        r = raw_block.get("bbox", (0, 0, 0, 0))
                        bbox = BoundingBox(
                            x0=r[0], y0=r[1], x1=r[2], y1=r[3],
                            page_width=page_w, page_height=page_h
                        )
                        blocks.append(DocumentBlock(
                            block_id=str(uuid.uuid4()),
                            block_type=BlockType.IMAGE,
                            content="",
                            page_number=page_num,
                            bbox=bbox,
                        ))
                        continue

                    if btype != 0:
                        continue  # skip unknown block types

                    # Assemble text and detect dominant font size in this block.
                    lines_text: list[str] = []
                    block_font_sizes: list[float] = []

                    for line in raw_block.get("lines", []):
                        line_parts: list[str] = []
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                line_parts.append(text)
                                sz = span.get("size", 0)
                                if sz > 0:
                                    block_font_sizes.append(sz)
                        if line_parts:
                            lines_text.append(" ".join(line_parts))

                    content = "\n".join(lines_text).strip()
                    if not content:
                        continue

                    # Determine block type from font size.
                    dominant_size = max(block_font_sizes) if block_font_sizes else median_font_size
                    block_type = (
                        BlockType.HEADING
                        if dominant_size >= heading_threshold
                        else BlockType.TEXT
                    )

                    r = raw_block.get("bbox", (0, 0, 0, 0))
                    bbox = BoundingBox(
                        x0=r[0], y0=r[1], x1=r[2], y1=r[3],
                        page_width=page_w, page_height=page_h
                    )

                    blocks.append(DocumentBlock(
                        block_id=str(uuid.uuid4()),
                        block_type=block_type,
                        content=content,
                        page_number=page_num,
                        bbox=bbox,
                    ))

            doc.close()

        except Exception as exc:
            logger.error(
                f"[PROCESSING] pdf_adapter.parse failed"
                f" document_id={self.document_id} error={exc}"
            )
            raise RuntimeError(f"PDF parsing failed: {exc}") from exc

        logger.info(
            f"[PROCESSING] pdf_adapter.parse completed document_id={self.document_id} "
            f"pages={page_count} blocks={len(blocks)}"
        )

        return NormalizedDocument(
            document_id=self.document_id,
            user_id=self.user_id,
            file_path=self.file_path,
            source_mime_type=self.mime_type,
            page_count=page_count,
            title=self.title,
            blocks=blocks,
            processing_metadata={"adapter": "PdfAdapter"},
        )
