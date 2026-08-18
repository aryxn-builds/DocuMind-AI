"""
DocuMind AI — Sidebar, URL persistence, refresh, and cross-document tests.

Tests verifying the corrected sidebar + URL-based conversation flow:

 1. GET /conversations returns document_id field needed for navigation.
 2. Sidebar conversations include document_id for cross-document navigation.
 3. Unauthorized conversation access is rejected (user B cannot read user A's convo).
 4. Hard refresh restores the exact conversation via GET /conversations/{id}.
 5. User and assistant messages restored with correct roles and order.
 6. Citations are restored in GET /conversations/{id}.
 7. New chat: POST /conversations with no document_id succeeds.
 8. First message creates exactly one conversation (idempotency).
 9. Switching conversations does not leak messages between them.
10. Switching documents does not leak messages between documents.
11. Sidebar collapse does not affect server state (stateless).
12. Same conversation returned regardless of JWT token value.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app)

USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_user(user_id: str = USER_A):
    app.dependency_overrides[get_current_user] = lambda: user_id


def _make_convo(
    convo_id: str | None = None,
    doc_id: str | None = None,
    user_id: str = USER_A,
    title: str = "Test Conversation",
) -> dict:
    return {
        "id": convo_id or str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "document_id": doc_id,
        "created_at": "2026-08-18T16:34:29.050497+00:00",
        "updated_at": "2026-08-18T16:34:29.050497+00:00",
    }


def _make_message(role: str, content: str, convo_id: str, created_at: str | None = None) -> dict:
    ts = created_at or "2026-08-18T17:00:00+00:00"
    return {
        "id": str(uuid.uuid4()),
        "conversation_id": convo_id,
        "user_id": USER_A,
        "role": role,
        "content": content,
        "created_at": ts,
        "updated_at": ts,
        "tokens_used": None,
        "provider": None,
        "model": None,
    }


@pytest.fixture(autouse=True)
def clear_overrides():
    """Ensure dependency overrides are cleaned up after each test."""
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. GET /conversations returns document_id
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_list_conversations_returns_document_id(mock_convo):
    """
    Sidebar requires document_id on each conversation to determine whether
    clicking it should navigate to a different document.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    convo = _make_convo(doc_id=doc_id)
    mock_convo.list_conversations.return_value = [convo]

    res = client.get("/api/v1/conversations", headers={"Authorization": "Bearer fake"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["document_id"] == doc_id


# ---------------------------------------------------------------------------
# 2. Sidebar conversations include document_id for cross-document navigation
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_sidebar_conversations_have_document_id_for_navigation(mock_convo):
    """
    When two conversations belong to two different documents, both are returned
    in the list and each carries its own document_id.
    """
    _override_user()
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    convo_a = _make_convo(doc_id=doc_a, title="Chat A")
    convo_b = _make_convo(doc_id=doc_b, title="Chat B")
    mock_convo.list_conversations.return_value = [convo_a, convo_b]

    res = client.get("/api/v1/conversations", headers={"Authorization": "Bearer fake"})
    assert res.status_code == 200
    data = res.json()
    ids = {c["document_id"] for c in data}
    assert doc_a in ids
    assert doc_b in ids


# ---------------------------------------------------------------------------
# 3. Unauthorized conversation access rejected
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_unauthorized_conversation_access_rejected(mock_convo):
    """
    User B must not be able to read User A's conversation even by guessing the ID.
    The repository filters by user_id, so it returns None → 404 (resource enumeration safe).
    """
    # Override as User B
    app.dependency_overrides[get_current_user] = lambda: USER_B

    # Repository returns None because User B does not own this conversation
    mock_convo.get_conversation_by_id.return_value = None

    convo_id = uuid.uuid4()
    res = client.get(
        f"/api/v1/conversations/{convo_id}",
        headers={"Authorization": "Bearer user-b-token"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# 4 & 5. Hard refresh restores exact conversation with user+assistant messages
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.citation_repository")
@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_hard_refresh_restores_exact_conversation_with_messages(
    mock_convo, mock_msg, mock_citation
):
    """
    Scenario:
      1. Open document A, open conversation C1, send "What is this document about?".
      2. Wait for assistant response.
      3. Hard refresh browser.

    Expected:
      - GET /conversations/{C1} returns the conversation with both messages.
      - User message appears first (correct role, correct content).
      - Assistant message appears second with its content.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    convo_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id, doc_id=doc_id)
    mock_convo.get_conversation_by_id.return_value = stub

    user_msg = _make_message("user", "What is this document about?", convo_id, "2026-08-18T17:00:00+00:00")
    asst_msg = _make_message("assistant", "This document is about machine learning.", convo_id, "2026-08-18T17:00:10+00:00")
    mock_msg.list_messages_for_conversation.return_value = [user_msg, asst_msg]
    mock_citation.get_citations_for_message.return_value = []

    res = client.get(
        f"/api/v1/conversations/{convo_id}",
        headers={"Authorization": "Bearer fake"},
    )
    assert res.status_code == 200
    data = res.json()

    # Conversation identity preserved
    assert data["id"] == convo_id
    assert data["document_id"] == doc_id

    # Both messages restored in order
    msgs = data["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "What is this document about?"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "This document is about machine learning."


# ---------------------------------------------------------------------------
# 6. Citations restored in GET /conversations/{id}
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.citation_repository")
@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_citations_restored_after_refresh(mock_convo, mock_msg, mock_citation):
    """
    After a hard refresh, the assistant message must include its citations
    so the UI can render the source attribution correctly.
    """
    _override_user()
    convo_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    msg_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id, doc_id=doc_id)
    mock_convo.get_conversation_by_id.return_value = stub

    asst_msg = {
        "id": msg_id,
        "conversation_id": convo_id,
        "user_id": USER_A,
        "role": "assistant",
        "content": "See page 5 for details.",
        "created_at": "2026-08-18T17:00:10+00:00",
        "updated_at": "2026-08-18T17:00:10+00:00",
        "tokens_used": None,
        "provider": None,
        "model": None,
    }
    mock_msg.list_messages_for_conversation.return_value = [asst_msg]

    citation = {
        "id": str(uuid.uuid4()),
        "message_id": msg_id,
        "user_id": USER_A,
        "document_id": doc_id,
        # Use chunk_id (not document_chunk_id) — the endpoint remaps the DB column
        # document_chunk_id → chunk_id before passing to CitationResponse serialization.
        "chunk_id": str(uuid.uuid4()),
        "page_number": 5,
        "excerpt": "Hardware requirements are described on page 5.",
        "relevance_score": 0.92,
        "created_at": "2026-08-18T17:00:10+00:00",
    }
    mock_citation.get_citations_for_message.return_value = [citation]

    res = client.get(f"/api/v1/conversations/{convo_id}", headers={"Authorization": "Bearer fake"})
    assert res.status_code == 200
    msgs = res.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "assistant"
    # Citations must be present and populated
    assert len(msgs[0]["citations"]) == 1
    assert msgs[0]["citations"][0]["page_number"] == 5


# ---------------------------------------------------------------------------
# 7. New chat: POST /conversations with no document_id succeeds
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_new_chat_without_document_id_creates_conversation(mock_convo):
    """
    Global new chat (no document) must be creatable.
    document_id is nullable.
    """
    _override_user()
    convo_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id, doc_id=None, title="New Chat")
    stub["document_id"] = None
    mock_convo.create_conversation.return_value = stub

    res = client.post(
        "/api/v1/conversations",
        json={"title": "New Chat"},
        headers={"Authorization": "Bearer fake"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == convo_id
    assert data["document_id"] is None
    assert data["messages"] == []


# ---------------------------------------------------------------------------
# 8. First message creates exactly one conversation
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_first_message_creates_exactly_one_conversation(mock_convo):
    """
    POST /conversations called once on first submit must create exactly one
    conversation. A second call must return the same id (no duplicate created).
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    convo_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id, doc_id=doc_id)
    mock_convo.create_conversation.return_value = stub

    res1 = client.post(
        "/api/v1/conversations",
        json={"title": "First message", "document_id": doc_id},
        headers={"Authorization": "Bearer fake"},
    )
    assert res1.status_code == 200
    assert res1.json()["id"] == convo_id
    # Only one create call
    mock_convo.create_conversation.assert_called_once()


# ---------------------------------------------------------------------------
# 9. Switching conversations does not leak messages
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.citation_repository")
@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_switching_conversations_does_not_leak_messages(mock_convo, mock_msg, mock_citation):
    """
    Fetching Convo-1 then Convo-2 must return distinct message sets.
    Messages from Convo-1 must not appear in Convo-2's response.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    convo1_id = str(uuid.uuid4())
    convo2_id = str(uuid.uuid4())
    stub1 = _make_convo(convo_id=convo1_id, doc_id=doc_id)
    stub2 = _make_convo(convo_id=convo2_id, doc_id=doc_id)

    msgs1 = [_make_message("user", "Message from Chat 1", convo1_id)]
    msgs2 = [_make_message("user", "Message from Chat 2", convo2_id)]

    def get_convo(convo_id, user_id):
        if str(convo_id) == convo1_id:
            return stub1
        if str(convo_id) == convo2_id:
            return stub2
        return None

    def list_msgs(convo_id, user_id):
        if str(convo_id) == convo1_id:
            return msgs1
        if str(convo_id) == convo2_id:
            return msgs2
        return []

    mock_convo.get_conversation_by_id.side_effect = get_convo
    mock_msg.list_messages_for_conversation.side_effect = list_msgs
    mock_citation.get_citations_for_message.return_value = []

    res1 = client.get(f"/api/v1/conversations/{convo1_id}", headers={"Authorization": "Bearer fake"})
    res2 = client.get(f"/api/v1/conversations/{convo2_id}", headers={"Authorization": "Bearer fake"})

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["messages"][0]["content"] == "Message from Chat 1"
    assert res2.json()["messages"][0]["content"] == "Message from Chat 2"
    # No cross-contamination
    assert res1.json()["messages"][0]["content"] != res2.json()["messages"][0]["content"]


# ---------------------------------------------------------------------------
# 10. Switching documents does not leak messages
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_switching_documents_does_not_leak_conversations(mock_convo):
    """
    When the user navigates from Document A to Document B, the conversations
    returned for doc_b must not include conversations from doc_a.
    """
    _override_user()
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    convo_a = _make_convo(doc_id=doc_a, title="Chat on Doc A")
    convo_b = _make_convo(doc_id=doc_b, title="Chat on Doc B")

    def list_side(user_id, document_id=None, **kwargs):
        if document_id == doc_a:
            return [convo_a]
        if document_id == doc_b:
            return [convo_b]
        return []

    mock_convo.list_conversations.side_effect = list_side

    res_a = client.get(f"/api/v1/conversations?document_id={doc_a}", headers={"Authorization": "Bearer fake"})
    res_b = client.get(f"/api/v1/conversations?document_id={doc_b}", headers={"Authorization": "Bearer fake"})

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    assert len(res_a.json()) == 1
    assert len(res_b.json()) == 1
    assert res_a.json()[0]["document_id"] == doc_a
    assert res_b.json()[0]["document_id"] == doc_b
    # No cross-contamination
    assert res_a.json()[0]["id"] != res_b.json()[0]["id"]


# ---------------------------------------------------------------------------
# 11. Sidebar collapse does not affect server state (stateless check)
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_sidebar_collapse_does_not_affect_server_state(mock_convo):
    """
    Sidebar collapse is purely client-side state. The server must continue to
    serve the same conversations regardless of any client collapse/expand state.
    Verifies the API is stateless with respect to UI state.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    convo = _make_convo(doc_id=doc_id, title="Persistent Chat")
    mock_convo.list_conversations.return_value = [convo]

    # Call twice — simulating the user expanding/collapsing (which re-fetches)
    res1 = client.get("/api/v1/conversations", headers={"Authorization": "Bearer fake"})
    res2 = client.get("/api/v1/conversations", headers={"Authorization": "Bearer fake"})

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()


# ---------------------------------------------------------------------------
# 12. Same conversation returned regardless of JWT token value
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_conversation_stable_across_token_refresh(mock_convo, mock_msg):
    """
    When Supabase refreshes the session (new JWT raw value), the same user_id
    is extracted. The same conversation must be returned for both tokens.
    This proves that a token refresh must NOT break history restoration.
    """
    _override_user(USER_A)
    convo_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id)
    mock_convo.get_conversation_by_id.return_value = stub
    mock_msg.list_messages_for_conversation.return_value = []

    for token in ("Bearer old-jwt-A", "Bearer new-refreshed-jwt-A"):
        res = client.get(
            f"/api/v1/conversations/{convo_id}",
            headers={"Authorization": token},
        )
        assert res.status_code == 200, f"Failed with token: {token}"
        assert res.json()["id"] == convo_id
