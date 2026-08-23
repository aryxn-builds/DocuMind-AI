"""
DocuMind AI — SSE Streaming reliability tests.

Verifies:
1.  SSE event split across two TCP chunks.
2.  Multiple events in one TCP chunk.
3.  Incomplete JSON inside an otherwise well-formed frame.
4.  Final event without trailing \\n\\n.
5.  Error event terminates stream.
6.  Stream of only [DONE] (empty content).
7.  \\r\\n line endings normalised correctly.
8.  Keepalive / comment frames are silently ignored.
9.  Backend StreamingResponse sets required SSE headers.
10. Backend generate_sse yields data: … \\n\\n format for every event type.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

# ---------------------------------------------------------------------------
# Helpers — a pure Python reimplementation of the frontend SSE parser so we
# can unit-test the same framing logic on the backend's output.
# ---------------------------------------------------------------------------

def _extract_sse_events(buffer: str):
    """
    Mirrors the extractSseEvents() function in ChatPanel.tsx.
    Returns (events_list, remaining_buffer).
    """
    events = []
    buf = buffer.replace("\r\n", "\n")
    boundary = buf.find("\n\n")
    while boundary != -1:
        frame = buf[:boundary]
        buf = buf[boundary + 2:]
        for line in frame.split("\n"):
            if not line.startswith("data: "):
                continue
            raw = line[6:].strip()
            if raw == "[DONE]":
                events.append({"kind": "done"})
                break
            if raw == "" or raw.startswith(":"):
                continue
            try:
                parsed = json.loads(raw)
                if parsed.get("type") == "citations":
                    events.append({"kind": "citations", "citations": parsed["citations"]})
                elif parsed.get("error"):
                    events.append({"kind": "error", "message": parsed["error"]})
                elif parsed.get("type") == "chunk" or "content" in parsed:
                    content = parsed.get("content", "")
                    if content:
                        events.append({"kind": "chunk", "content": content})
            except json.JSONDecodeError:
                pass  # Non-fatal — partial frame
        boundary = buf.find("\n\n")
    return events, buf


# ---------------------------------------------------------------------------
# 1. SSE event split across two TCP chunks
# ---------------------------------------------------------------------------
def test_sse_split_across_chunks():
    """Two chunks together form one complete SSE frame."""
    chunk1 = 'data: {"type": "chunk", "cont'
    chunk2 = 'ent": "hello"}\n\n'
    buffer = chunk1 + chunk2
    events, remaining = _extract_sse_events(buffer)
    assert len(events) == 1
    assert events[0] == {"kind": "chunk", "content": "hello"}
    assert remaining == ""


# ---------------------------------------------------------------------------
# 2. Multiple events in one TCP chunk
# ---------------------------------------------------------------------------
def test_multiple_events_in_one_chunk():
    frames = (
        'data: {"type": "chunk", "content": "first"}\n\n'
        'data: {"type": "chunk", "content": "second"}\n\n'
        'data: [DONE]\n\n'
    )
    events, remaining = _extract_sse_events(frames)
    assert len(events) == 3
    assert events[0] == {"kind": "chunk", "content": "first"}
    assert events[1] == {"kind": "chunk", "content": "second"}
    assert events[2] == {"kind": "done"}
    assert remaining == ""


# ---------------------------------------------------------------------------
# 3. Incomplete JSON inside a well-formed frame — non-fatal
# ---------------------------------------------------------------------------
def test_incomplete_json_is_non_fatal():
    frames = (
        'data: {broken json\n\n'
        'data: {"type": "chunk", "content": "ok"}\n\n'
    )
    events, remaining = _extract_sse_events(frames)
    # The broken frame is silently skipped; the valid one is returned.
    assert len(events) == 1
    assert events[0]["content"] == "ok"


# ---------------------------------------------------------------------------
# 4. Final event without trailing \\n\\n stays in buffer (not dropped)
# ---------------------------------------------------------------------------
def test_incomplete_frame_stays_in_buffer():
    """If the last frame has no \\n\\n delimiter it must remain in the buffer."""
    frames = (
        'data: {"type": "chunk", "content": "first"}\n\n'
        'data: {"type": "chunk", "content": "second"}'  # No trailing \n\n
    )
    events, remaining = _extract_sse_events(frames)
    assert len(events) == 1
    assert events[0]["content"] == "first"
    # The incomplete frame is in remaining, ready to be joined with the next network chunk.
    assert '"second"' in remaining


def test_incomplete_frame_completed_by_next_chunk():
    """Simulates two network reads where the second completes the first frame."""
    # First read — incomplete frame
    _, buf = _extract_sse_events('data: {"type": "chunk", "content": "hel')
    assert buf == 'data: {"type": "chunk", "content": "hel'

    # Second read — completes the frame
    events, buf2 = _extract_sse_events(buf + 'lo"}\n\n')
    assert len(events) == 1
    assert events[0]["content"] == "hello"
    assert buf2 == ""


# ---------------------------------------------------------------------------
# 5. Error event
# ---------------------------------------------------------------------------
def test_error_event_parsed():
    frame = 'data: {"error": "Something went wrong"}\n\n'
    events, _ = _extract_sse_events(frame)
    assert len(events) == 1
    assert events[0] == {"kind": "error", "message": "Something went wrong"}


# ---------------------------------------------------------------------------
# 6. Only [DONE] — empty stream
# ---------------------------------------------------------------------------
def test_done_only_produces_done_event():
    frame = "data: [DONE]\n\n"
    events, remaining = _extract_sse_events(frame)
    assert events == [{"kind": "done"}]
    assert remaining == ""


# ---------------------------------------------------------------------------
# 7. \\r\\n line endings
# ---------------------------------------------------------------------------
def test_crlf_line_endings_normalised():
    frame = 'data: {"type": "chunk", "content": "crlf"}\r\n\r\n'
    events, _ = _extract_sse_events(frame)
    assert len(events) == 1
    assert events[0]["content"] == "crlf"


# ---------------------------------------------------------------------------
# 8. Keepalive / comment frames are silently ignored
# ---------------------------------------------------------------------------
def test_keepalive_frame_ignored():
    frames = (
        ": keepalive\n\n"
        'data: {"type": "chunk", "content": "real"}\n\n'
    )
    events, _ = _extract_sse_events(frames)
    # The ": keepalive" comment frame produces no event.
    assert len(events) == 1
    assert events[0]["content"] == "real"


def test_empty_data_line_ignored():
    frames = "data: \n\ndata: \n\n"
    events, _ = _extract_sse_events(frames)
    assert events == []


# ---------------------------------------------------------------------------
# 9. Backend StreamingResponse sets required SSE headers
# ---------------------------------------------------------------------------

TEST_USER = str(uuid.uuid4())
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def _override_user(user_id: str = TEST_USER):
    app.dependency_overrides[get_current_user] = lambda: user_id


@patch("app.api.v1.endpoints.chat.conversation_repository")
@patch("app.api.v1.endpoints.chat.rag_service")
def test_stream_response_headers(mock_rag, mock_convo_repo):
    _override_user()
    convo_id = str(uuid.uuid4())
    convo_stub = {
        "id": convo_id,
        "user_id": TEST_USER,
        "title": "Test",
        "document_id": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    mock_convo_repo.get_conversation_by_id.return_value = convo_stub

    # Async generator that yields one chunk then stops
    async def _fake_stream(*args, **kwargs):
        yield {"type": "chunk", "content": "hello"}

    mock_rag.stream_chat = _fake_stream

    response = client.post(
        f"/api/v1/conversations/{convo_id}/messages",
        json={"query": "hi", "document_id": convo_stub["document_id"]},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("x-accel-buffering") == "no"


# ---------------------------------------------------------------------------
# 10. Backend generate_sse yields correct SSE framing
# ---------------------------------------------------------------------------
@patch("app.api.v1.endpoints.chat.conversation_repository")
@patch("app.api.v1.endpoints.chat.rag_service")
def test_stream_body_is_correct_sse_format(mock_rag, mock_convo_repo):
    _override_user()
    convo_id = str(uuid.uuid4())
    convo_stub = {
        "id": convo_id,
        "user_id": TEST_USER,
        "title": "Test",
        "document_id": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    mock_convo_repo.get_conversation_by_id.return_value = convo_stub

    async def _fake_stream(*args, **kwargs):
        yield {"type": "chunk", "content": "world"}
        yield {"type": "citations", "citations": []}

    mock_rag.stream_chat = _fake_stream

    response = client.post(
        f"/api/v1/conversations/{convo_id}/messages",
        json={"query": "hi", "document_id": convo_stub["document_id"]},
        headers={"Authorization": "Bearer fake"},
    )

    body = response.text
    # Every SSE frame must start with "data: " and end with "\n\n"
    lines = [l for l in body.split("\n\n") if l.strip()]
    for line in lines:
        assert line.startswith("data: "), f"Frame does not start with 'data: ': {line!r}"

    # The body must end with the [DONE] sentinel
    assert "data: [DONE]" in body

    # Verify the chunk event contains correct JSON
    chunk_frames = [l for l in body.split("\n\n") if '"chunk"' in l]
    assert len(chunk_frames) >= 1
    payload = json.loads(chunk_frames[0][len("data: "):])
    assert payload["type"] == "chunk"
    assert payload["content"] == "world"
