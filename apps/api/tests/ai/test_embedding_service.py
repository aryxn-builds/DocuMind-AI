import uuid

import pytest

from app.ai.embedding_service import GEMINI_EMBEDDING_MODEL, EmbeddingService
from app.ai.models import Chunk


def test_embedding_model_name_is_correct():
    assert GEMINI_EMBEDDING_MODEL == "gemini-embedding-2"
    assert "text-embedding-004" not in GEMINI_EMBEDDING_MODEL
    assert "gemini-embedding-001" not in GEMINI_EMBEDDING_MODEL


def _make_chunk(content: str, index: int = 0) -> Chunk:
    """Helper to create a test Chunk."""
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        user_id="test_user_123",
        chunk_index=index,
        chunk_type="TEXT",
        content=content,
        page_number=1,
    )


@pytest.mark.asyncio
async def test_single_text_produces_single_embedding():
    """1 text → 1 embedding → 768 dimensions."""
    service = EmbeddingService()
    chunk = _make_chunk("Single text embedding test.")
    results = service.embed([chunk])

    assert len(results) == 1
    returned_chunk, vector = results[0]
    assert returned_chunk.chunk_id == chunk.chunk_id
    assert len(vector) == 768, (
        f"Expected 768 dimensions, got {len(vector)}"
    )


@pytest.mark.asyncio
async def test_five_texts_produce_five_embeddings():
    """5 texts → 5 embeddings → each 768 dimensions.

    This is the exact scenario that was broken when contents was
    passed as a bare list of strings (produced 1 embedding for 5 texts).
    """
    service = EmbeddingService()
    texts = ["alpha", "bravo", "charlie", "delta", "echo"]
    chunks = [_make_chunk(t, i) for i, t in enumerate(texts)]

    results = service.embed(chunks)

    assert len(results) == 5, (
        f"Expected 5 embeddings, got {len(results)}"
    )
    for i, (chunk, vector) in enumerate(results):
        assert chunk.chunk_id == chunks[i].chunk_id
        assert len(vector) == 768, (
            f"Embedding {i} has {len(vector)} dims, expected 768"
        )


@pytest.mark.asyncio
async def test_query_embedding_768():
    """Query embedding → 768 dimensions."""
    service = EmbeddingService()
    vector = service.embed_query("What is machine learning?")
    assert len(vector) == 768, (
        f"Expected 768 dimensions for query, got {len(vector)}"
    )
