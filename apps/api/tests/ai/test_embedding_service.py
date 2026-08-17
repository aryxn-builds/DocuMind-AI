import uuid

import pytest

from app.ai.embedding_service import GEMINI_EMBEDDING_MODEL, EmbeddingService
from app.ai.models import Chunk


def test_embedding_model_name_is_correct():
    assert GEMINI_EMBEDDING_MODEL == "gemini-embedding-2"
    assert "text-embedding-004" not in GEMINI_EMBEDDING_MODEL
    assert "gemini-embedding-001" not in GEMINI_EMBEDDING_MODEL

@pytest.mark.asyncio
async def test_live_embedding_generation():
    """
    Focused live embedding test to verify:
    1. Gemini API request succeeds
    2. Returned vector dimension == 768
    """
    service = EmbeddingService()

    # Create a test chunk
    chunk = Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        user_id="test_user_123",
        chunk_index=0,
        chunk_type="TEXT",
        content="This is a test chunk to verify the new Gemini embedding model.",
        page_number=1,
    )

    # 1. Verify batch document embedding
    results = service.embed([chunk])
    assert len(results) == 1

    returned_chunk, vector = results[0]
    assert returned_chunk.chunk_id == chunk.chunk_id

    # 2. Verify returned vector dimension == 768
    assert len(vector) == 768, f"Expected 768 dimensions, got {len(vector)}"

    # 3. Verify query embedding
    query_vector = service.embed_query("This is a search query test.")
    assert len(query_vector) == 768, f"Expected 768 dimensions for query, got {len(query_vector)}"
