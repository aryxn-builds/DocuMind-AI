from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    TEXT = "text"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"
    LIST = "list"
    CAPTION = "caption"


@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float
    page_width: float
    page_height: float


@dataclass
class DocumentBlock:
    block_id: str
    block_type: BlockType
    content: str
    page_number: int | None = None
    section_path: list[str] = field(default_factory=list)
    bbox: BoundingBox | None = None
    table_data: list[list[str]] | None = None
    image_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedDocument:
    document_id: str
    user_id: str
    file_path: str
    source_mime_type: str
    page_count: int
    title: str
    blocks: list[DocumentBlock]
    processing_metadata: dict[str, Any]


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    user_id: str
    chunk_index: int
    chunk_type: str
    content: str
    page_number: int | None = None
    section_path: list[str] = field(default_factory=list)
    bbox: BoundingBox | None = None
    table_data: list[list[str]] | None = None
    image_ref: str | None = None
    source_block_ids: list[str] = field(default_factory=list)
    content_preview: str = ""
