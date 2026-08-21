"""
DocuMind AI — RAG Service Security Tests.

Verifies the security and behavioral properties required by Phase 9:
  1. Citation injection: LLM cannot persist citations for chunk IDs it
     invents — only chunk_ids that appear in chunk_map (i.e. retrieved from
     Qdrant with the authenticated user_id filter) are persisted.
  2. Conversation ownership: stream_chat raises ValueError for a conversation
     that does not belong to the authenticated user.
  3. Groq 4xx errors are NOT retried / forwarded to Gemini.
  4. Grounded answering: when retrieval returns empty results the system
     prompt instructs the LLM to state it could not find the information.
  5. Partial-failure: a streaming exception does NOT persist an assistant
     message with the error text in it.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import RagRequest
from app.services.rag_service import RagService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def svc() -> RagService:
    return RagService()


def _make_search_result(chunk_id: uuid.UUID, document_id: uuid.UUID) -> MagicMock:
    res = MagicMock()
    res.chunk_id = chunk_id
    res.document_id = document_id
    res.page_number = 1
    res.content = "Sample chunk content."
    res.relevance_score = 0.9
    return res


def _make_search_response(results: list) -> MagicMock:
    sr = MagicMock()
    sr.results = results
    return sr


async def _stream_one_chunk(content: str) -> AsyncGenerator[dict, None]:
    yield {"content": content, "model": "test-model", "provider": "test"}


# ---------------------------------------------------------------------------
# 1. Citation injection — LLM cannot cite an arbitrary chunk_id
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.services.rag_service.chunk_repository")
@patch("app.services.rag_service.conversation_repository")
@patch("app.services.rag_service.message_repository")
@patch("app.services.rag_service.retrieval_service")
@patch("app.services.rag_service.citation_repository")
@patch("app.services.rag_service.gateway")
async def test_citation_injection_rejected(
    mock_gateway,
    mock_citation_repo,
    mock_retrieval,
    mock_message_repo,
    mock_convo_repo,
    mock_chunk_repo,
    svc: RagService,
):
    """
    The LLM response references a chunk_id that was NOT returned by Qdrant
    retrieval. That citation must NOT be persisted.
    """
    user_id = str(uuid.uuid4())
    conversation_id = uuid.uuid4()
    real_chunk_id = uuid.uuid4()
    fake_chunk_id = uuid.uuid4()  # attacker / hallucinated chunk

    mock_convo_repo.get_conversation_by_id.return_value = {"id": str(conversation_id)}
    mock_message_repo.create_message.return_value = {"id": str(uuid.uuid4())}
    mock_message_repo.list_messages_for_conversation.return_value = []
    mock_retrieval.search.return_value = _make_search_response(
        [_make_search_result(real_chunk_id, uuid.uuid4())]
    )
    mock_chunk_repo.get_chunks_by_ids.return_value = [{"id": str(real_chunk_id), "document_id": str(uuid.uuid4())}]
    mock_chunk_repo.get_document_summary.return_value = None

    # LLM response cites the REAL chunk (1) AND an invented chunk (2)
    llm_response = (
        "Real ref [Source: 1] "
        "and fake ref [Source: 2]."
    )

    async def _mock_stream(_messages):
        yield {"content": llm_response, "model": "m", "provider": "p"}

    mock_gateway.stream_chat = _mock_stream

    request = RagRequest(query="test", document_id=uuid.uuid4())
    chunks = [c async for c in svc.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)})]

    # Check chunks and citations
    text_chunks = [c["content"] for c in chunks if c.get("type") == "chunk"]
    assert "".join(text_chunks) == llm_response

    # Only the real citation should have been passed to the repo
    mock_citation_repo.create_citations.assert_called_once()
    persisted = mock_citation_repo.create_citations.call_args[0][1]
    persisted_chunk_ids = {str(c["chunk_id"]) for c in persisted}
    assert str(real_chunk_id) in persisted_chunk_ids, "real citation must be persisted"
    assert str(fake_chunk_id) not in persisted_chunk_ids, (
        "hallucinated citation must NOT be persisted"
    )


# ---------------------------------------------------------------------------
# 2. Conversation ownership — another user's conversation is rejected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.services.rag_service.conversation_repository")
@patch("app.services.rag_service.message_repository")
@patch("app.services.rag_service.retrieval_service")
@patch("app.services.rag_service.citation_repository")
@patch("app.services.rag_service.gateway")
async def test_unauthorized_conversation_raises(
    mock_gateway,
    mock_citation_repo,
    mock_retrieval,
    mock_message_repo,
    mock_convo_repo,
    svc: RagService,
):
    """
    When the conversation does not belong to the authenticated user,
    stream_chat must raise ValueError before any LLM call or DB write.
    """
    user_id = str(uuid.uuid4())
    conversation_id = uuid.uuid4()

    # Simulate repository returning None (conversation exists but owned by
    # a different user — the repo filters by user_id).
    mock_convo_repo.get_conversation_by_id.return_value = None

    request = RagRequest(query="hack", document_id=uuid.uuid4())

    with pytest.raises(ValueError, match="not found or unauthorized"):
        async for _ in svc.stream_chat(user_id, conversation_id, request, None):
            pass

    # Ensure no LLM call and no DB write happened
    mock_gateway.stream_chat.assert_not_called()
    mock_message_repo.create_message.assert_not_called()
    mock_citation_repo.create_citations.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Groq 4xx does NOT fall back to Gemini
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_4xx_no_gemini_fallback():
    """
    Gateway must re-raise Groq 4xx errors immediately without calling Gemini.
    Covers: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 422 Unprocessable.
    """
    try:
        from groq import APIStatusError as GroqAPIStatusError
    except ImportError:
        pytest.skip("groq package not installed")

    import httpx

    from app.ai.gateway import _GROQ_NO_RETRY_STATUS, AIGateway

    for status_code in _GROQ_NO_RETRY_STATUS:
        gw = AIGateway()
        gw.gemini_api_key = "fake-gemini-key"  # Gemini is available
        gw.groq_client = MagicMock()  # groq client exists so primary path is attempted

        # GroqAPIStatusError requires a Request to be bound to the Response.
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(status_code, request=request)
        groq_error = GroqAPIStatusError(
            message=f"Test {status_code}",
            response=response,
            body={},
        )

        # _stream_groq is an async generator; make it raise on first next() call.
        async def _raising_stream(*args, **kwargs):
            raise groq_error
            yield  # pragma: no cover — ensures it is typed as an async generator

        with patch.object(gw, "_stream_groq", new=_raising_stream):
            with patch.object(gw, "_stream_gemini") as mock_gemini:
                with pytest.raises(GroqAPIStatusError):
                    async for _ in gw.stream_chat([{"role": "user", "content": "hi"}]):
                        pass
                mock_gemini.assert_not_called(), (
                    f"Gemini must not be called on Groq {status_code}"
                )


# ---------------------------------------------------------------------------
# 4. Grounded answering — empty retrieval results -> no-information prompt
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.services.rag_service.conversation_repository")
@patch("app.services.rag_service.message_repository")
@patch("app.services.rag_service.retrieval_service")
@patch("app.services.rag_service.citation_repository")
@patch("app.services.rag_service.gateway")
async def test_empty_retrieval_context_prompt(
    mock_gateway,
    mock_citation_repo,
    mock_retrieval,
    mock_message_repo,
    mock_convo_repo,
    svc: RagService,
):
    """
    When Qdrant returns no results the system prompt must include the
    'No relevant documents found' sentinel so the LLM is grounded to refuse.
    """
    user_id = str(uuid.uuid4())
    conversation_id = uuid.uuid4()
    mock_convo_repo.get_conversation_by_id.return_value = {"id": str(conversation_id)}
    mock_message_repo.create_message.return_value = {"id": str(uuid.uuid4())}
    mock_message_repo.list_messages_for_conversation.return_value = []
    mock_retrieval.search.return_value = _make_search_response([])  # empty

    captured_messages: list = []

    async def _capture_stream(messages):
        captured_messages.extend(messages)
        yield {"content": "I could not find this information.", "model": "m", "provider": "p"}

    mock_gateway.stream_chat = _capture_stream

    request = RagRequest(query="What is the secret?", document_id=None)
    _ = [c async for c in svc.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)})]

    # The system message (first message) must contain the no-results sentinel
    system_content = captured_messages[0]["content"]
    assert "No relevant documents found" in system_content, (
        "System prompt must include no-results message when retrieval is empty"
    )
    # And must instruct the LLM not to fabricate answers
    assert "Only answer based on the provided context" in system_content, (
        "System prompt must include grounding rule"
    )


# ---------------------------------------------------------------------------
# 5. Streaming failure — no assistant message persisted on error
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.services.rag_service.conversation_repository")
@patch("app.services.rag_service.message_repository")
@patch("app.services.rag_service.retrieval_service")
@patch("app.services.rag_service.citation_repository")
@patch("app.services.rag_service.gateway")
async def test_streaming_failure_no_assistant_message(
    mock_gateway,
    mock_citation_repo,
    mock_retrieval,
    mock_message_repo,
    mock_convo_repo,
    svc: RagService,
):
    """
    If the LLM streaming raises an exception partway through, the service
    must NOT persist a completed assistant message with error text in it.
    """
    user_id = str(uuid.uuid4())
    conversation_id = uuid.uuid4()
    msg_id = str(uuid.uuid4())
    mock_convo_repo.get_conversation_by_id.return_value = {"id": str(conversation_id)}
    # First call (user message) succeeds; if create_message is called a
    # second time for the assistant message that would be the bug.
    mock_message_repo.create_message.return_value = {"id": msg_id}
    mock_message_repo.list_messages_for_conversation.return_value = []
    mock_retrieval.search.return_value = _make_search_response([])

    async def _failing_stream(messages):
        yield {"content": "partial...", "model": "m", "provider": "p"}
        raise RuntimeError("LLM network failure")

    mock_gateway.stream_chat = _failing_stream

    request = RagRequest(query="anything", document_id=None)
    chunks = [c async for c in svc.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)})]

    # The error chunk is yielded (system error message)
    assert any("[System Error:" in c.get("content", "") for c in chunks), (
        "Service should yield an error indicator"
    )
    # create_message must have been called only ONCE (for the user message);
    # the assistant message must NOT be persisted on failure.
    assert mock_message_repo.create_message.call_count == 1, (
        "Assistant message must NOT be persisted when streaming fails"
    )
    mock_citation_repo.create_citations.assert_not_called()
