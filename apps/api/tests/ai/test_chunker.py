from app.ai.chunker import Chunker
from app.ai.models import BlockType, DocumentBlock, NormalizedDocument


def test_chunker_groups_text_blocks():
    chunker = Chunker()
    chunker.MIN_CHUNK_CHARS = 10

    doc = NormalizedDocument(
        document_id="doc-123",
        user_id="user-123",
        file_path="test.pdf",
        source_mime_type="application/pdf",
        page_count=1,
        title="Test Doc",
        processing_metadata={},
        blocks=[
            DocumentBlock(block_id="b1", content="Hello world.", block_type=BlockType.TEXT),
            DocumentBlock(block_id="b2", content=" This is a test.", block_type=BlockType.TEXT),
        ]
    )

    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert "Hello world." in chunks[0].content
    assert chunks[0].source_block_ids == ["b1", "b2"]

def test_chunker_handles_image_blocks():
    chunker = Chunker()
    chunker.MIN_CHUNK_CHARS = 10

    doc = NormalizedDocument(
        document_id="doc-123",
        user_id="user-123",
        file_path="test.pdf",
        source_mime_type="application/pdf",
        page_count=1,
        title="Test Doc",
        processing_metadata={},
        blocks=[
            DocumentBlock(block_id="b1", content="Text before.", block_type=BlockType.TEXT),
            DocumentBlock(block_id="img1", content="An image description", block_type=BlockType.IMAGE),
            DocumentBlock(block_id="b2", content="Text after.", block_type=BlockType.TEXT),
        ]
    )

    chunks = chunker.chunk(doc)
    assert len(chunks) == 3
    assert chunks[0].content == "Text before."
    assert chunks[1].content == "An image description"
    assert chunks[1].chunk_type == "image"
    assert chunks[2].content == "Text after."
