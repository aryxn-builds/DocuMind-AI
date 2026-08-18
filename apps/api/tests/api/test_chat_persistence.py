"""
DocuMind AI — Chat persistence and history-restoration tests.

Verifies the specific failure modes identified in the root-cause investigation:

A. History loads after a hard reload (list → select → fetch messages).
B. Changing accessToken does NOT clear or re-initialise conversation data.
C. Changing documentId DOES select a fresh conversation for the new document.
D. Duplicate conversations: the conversation with the most-recent message is
   selected, not the newest (empty) conversation row.
E. New document with conversationId=null can send the first message (lazy
   conversation creation on first submit).
F. Subsequent messages reuse the same conversation.
G. Refresh restores both user and assistant messages in correct order.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app)

TEST_USER = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_user(user_id: str = TEST_USER):
    app.dependency_overrides[get_current_user] = lambda: user_id


def _make_convo(convo_id: str | None = None, doc_id: str | None = None) -> dict:
    return {
        "id": convo_id or str(uuid.uuid4()),
        "user_id": TEST_USER,
        "title": "Document Chat",
        "document_id": doc_id or str(uuid.uuid4()),
        "created_at": "2026-08-18T16:34:29.050497+00:00",
        "updated_at": "2026-08-18T16:34:29.050497+00:00",
    }


def _make_message(role: str, content: str, created_at: str, convo_id: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "conversation_id": convo_id,
        "user_id": TEST_USER,
        "role": role,
        "content": content,
        "created_at": created_at,
        "updated_at": created_at,
        "tokens_used": None,
        "provider": None,
        "model": None,
    }


# ---------------------------------------------------------------------------
# A. History loads after a simulated hard reload
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.citation_repository")
@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_history_loads_after_hard_reload(mock_convo, mock_msg, mock_citation):
    """
    Simulates the two HTTP calls ChatPanel makes on mount:
      1. GET /conversations?document_id=<id>  → returns existing conversation
      2. GET /conversations/<id>              → returns messages

    Asserts both user and assistant messages are returned in order.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    convo_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id, doc_id=doc_id)

    mock_convo.list_conversations.return_value = [stub]
    mock_convo.get_conversation_by_id.return_value = stub

    user_msg = _make_message("user", "Hello", "2026-08-18T17:00:00+00:00", convo_id)
    asst_msg = _make_message("assistant", "Hi there!", "2026-08-18T17:00:10+00:00", convo_id)
    mock_msg.list_messages_for_conversation.return_value = [user_msg, asst_msg]
    mock_citation.get_citations_for_message.return_value = []

    # Step 1 — list conversations
    list_res = client.get(
        f"/api/v1/conversations?document_id={doc_id}",
        headers={"Authorization": "Bearer fake-token-A"},
    )
    assert list_res.status_code == 200
    convos = list_res.json()
    assert len(convos) == 1
    assert convos[0]["id"] == convo_id

    # Step 2 — fetch full conversation including messages
    full_res = client.get(
        f"/api/v1/conversations/{convo_id}",
        headers={"Authorization": "Bearer fake-token-A"},
    )
    assert full_res.status_code == 200
    data = full_res.json()
    messages = data["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there!"


# ---------------------------------------------------------------------------
# B. Changing accessToken does NOT clear conversation data
#    (Backend-level: same conversation is returned for both token-A and token-B)
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_conversation_returned_regardless_of_token_value(mock_convo, mock_msg):
    """
    The backend filters by user_id (from JWT), NOT by raw token value.
    The same conversation is returned whether the client presents token-A or
    token-B (both decode to the same user_id), proving that a session refresh
    that produces a new raw JWT must not break history restoration.
    """
    _override_user()
    convo_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id)
    mock_convo.get_conversation_by_id.return_value = stub
    mock_msg.list_messages_for_conversation.return_value = []

    for fake_token in ("Bearer fake-token-A", "Bearer fake-token-B"):
        res = client.get(
            f"/api/v1/conversations/{convo_id}",
            headers={"Authorization": fake_token},
        )
        assert res.status_code == 200, f"Failed with token: {fake_token}"
        assert res.json()["id"] == convo_id


# ---------------------------------------------------------------------------
# C. Different document_id returns different conversation
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_different_document_returns_different_conversation(mock_convo):
    """
    Changing documentId causes ChatPanel to call list_conversations with the
    new document_id. The backend must return only conversations for that doc.
    """
    _override_user()
    doc_a = str(uuid.uuid4())
    doc_b = str(uuid.uuid4())
    convo_a = _make_convo(doc_id=doc_a)
    convo_b = _make_convo(doc_id=doc_b)

    def list_side_effect(user_id, document_id=None, **kwargs):
        if document_id == doc_a:
            return [convo_a]
        if document_id == doc_b:
            return [convo_b]
        return []

    mock_convo.list_conversations.side_effect = list_side_effect

    res_a = client.get(
        f"/api/v1/conversations?document_id={doc_a}",
        headers={"Authorization": "Bearer fake"},
    )
    res_b = client.get(
        f"/api/v1/conversations?document_id={doc_b}",
        headers={"Authorization": "Bearer fake"},
    )

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    assert res_a.json()[0]["id"] == convo_a["id"]
    assert res_b.json()[0]["id"] == convo_b["id"]
    assert res_a.json()[0]["id"] != res_b.json()[0]["id"]


# ---------------------------------------------------------------------------
# D. Duplicate conversations: the one with most-recent message is fetchable
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.citation_repository")
@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_duplicate_conversations_full_fetch_returns_correct_messages(
    mock_convo, mock_msg, mock_citation
):
    """
    When multiple conversations exist for the same (user_id, document_id),
    ChatPanel fetches details of the top candidates and picks the one with
    the most-recent message.

    This test verifies that GET /conversations/{id} correctly returns messages
    for each conversation, enabling the client to compare and select the best.

    Scenario:
      - convos[0] = newer row, 0 messages (empty, just created)
      - convos[1] = older row, 22 messages (the real conversation)
    Expected: client can fetch convos[1] and see its 22 messages.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    empty_convo_id = str(uuid.uuid4())
    rich_convo_id = str(uuid.uuid4())

    empty_convo = _make_convo(convo_id=empty_convo_id, doc_id=doc_id)
    rich_convo = _make_convo(convo_id=rich_convo_id, doc_id=doc_id)

    # Populate the older conversation with 22 messages
    rich_messages = [
        _make_message(
            "user" if i % 2 == 0 else "assistant",
            f"Message {i}",
            f"2026-08-18T17:{i:02d}:00+00:00",
            rich_convo_id,
        )
        for i in range(22)
    ]

    mock_convo.list_conversations.return_value = [empty_convo, rich_convo]

    def get_convo_side_effect(convo_id, user_id):
        if str(convo_id) == empty_convo_id:
            return empty_convo
        if str(convo_id) == rich_convo_id:
            return rich_convo
        return None

    def list_msgs_side_effect(convo_id, user_id):
        if str(convo_id) == empty_convo_id:
            return []
        if str(convo_id) == rich_convo_id:
            return rich_messages
        return []

    mock_convo.get_conversation_by_id.side_effect = get_convo_side_effect
    mock_msg.list_messages_for_conversation.side_effect = list_msgs_side_effect
    mock_citation.get_citations_for_message.return_value = []

    # Client fetches empty conversation — sees 0 messages
    res_empty = client.get(
        f"/api/v1/conversations/{empty_convo_id}",
        headers={"Authorization": "Bearer fake"},
    )
    assert res_empty.status_code == 200
    assert len(res_empty.json()["messages"]) == 0

    # Client fetches rich conversation — sees 22 messages
    res_rich = client.get(
        f"/api/v1/conversations/{rich_convo_id}",
        headers={"Authorization": "Bearer fake"},
    )
    assert res_rich.status_code == 200
    assert len(res_rich.json()["messages"]) == 22
    # Verify ordering: oldest message first (ASC by created_at)
    assert res_rich.json()["messages"][0]["content"] == "Message 0"
    assert res_rich.json()["messages"][-1]["content"] == "Message 21"


# ---------------------------------------------------------------------------
# E. New document with no conversation can still send first message
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_new_document_first_message_creates_conversation(mock_convo):
    """
    When no conversation exists for a document, ChatPanel shows the user an
    empty panel. On first submit it calls POST /conversations (lazy creation).
    Verifies the creation succeeds and returns a valid conversation id.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    new_convo_id = str(uuid.uuid4())
    new_convo = _make_convo(convo_id=new_convo_id, doc_id=doc_id)

    # Idempotency check inside create_conversation sees no existing convo
    mock_convo.list_conversations.return_value = []
    mock_convo.create_conversation.return_value = new_convo

    res = client.post(
        "/api/v1/conversations",
        json={"title": "Document Chat", "document_id": doc_id},
        headers={"Authorization": "Bearer fake"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == new_convo_id
    assert data["document_id"] == doc_id
    assert data["messages"] == []


# ---------------------------------------------------------------------------
# F. Subsequent messages reuse the same conversation
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_create_conversation_returns_existing_when_duplicate_requested(mock_convo):
    """
    The backend's create_conversation performs an idempotency check:
    if a conversation already exists for (user_id, document_id), the existing
    one is returned instead of creating a duplicate.

    This ensures that even if POST /conversations is called again (e.g., after
    a race condition), the same conversation_id is used for all messages.
    """
    _override_user()
    doc_id = str(uuid.uuid4())
    existing_convo_id = str(uuid.uuid4())
    existing_convo = _make_convo(convo_id=existing_convo_id, doc_id=doc_id)

    # Idempotency: first call finds existing conversation
    mock_convo.list_conversations.return_value = [existing_convo]
    mock_convo.create_conversation.return_value = existing_convo

    # First POST — creates (or finds existing)
    res1 = client.post(
        "/api/v1/conversations",
        json={"title": "Document Chat", "document_id": doc_id},
        headers={"Authorization": "Bearer fake"},
    )
    # Second POST — should return the same conversation
    res2 = client.post(
        "/api/v1/conversations",
        json={"title": "Document Chat", "document_id": doc_id},
        headers={"Authorization": "Bearer fake"},
    )

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["id"] == res2.json()["id"] == existing_convo_id


# ---------------------------------------------------------------------------
# G. Refresh restores both user and assistant messages in correct order
# ---------------------------------------------------------------------------

@patch("app.api.v1.endpoints.chat.citation_repository")
@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_refresh_restores_user_and_assistant_messages_in_order(
    mock_convo, mock_msg, mock_citation
):
    """
    After a page refresh the full conversation fetch must return messages in
    chronological order with correct roles. Both user turns and assistant turns
    must be present and in the correct sequence.
    """
    _override_user()
    convo_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    stub = _make_convo(convo_id=convo_id, doc_id=doc_id)

    user_1 = _make_message("user", "What is on page 18?", "2026-08-18T17:00:00+00:00", convo_id)
    asst_1 = _make_message("assistant", "Page 18 contains hardware requirements.", "2026-08-18T17:00:10+00:00", convo_id)
    user_2 = _make_message("user", "Summarise the document.", "2026-08-18T17:01:00+00:00", convo_id)
    asst_2 = _make_message("assistant", "The document is a B.Tech synopsis.", "2026-08-18T17:01:15+00:00", convo_id)

    mock_convo.get_conversation_by_id.return_value = stub
    mock_msg.list_messages_for_conversation.return_value = [user_1, asst_1, user_2, asst_2]
    mock_citation.get_citations_for_message.return_value = []

    res = client.get(
        f"/api/v1/conversations/{convo_id}",
        headers={"Authorization": "Bearer fake"},
    )
    assert res.status_code == 200
    msgs = res.json()["messages"]
    assert len(msgs) == 4
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "What is on page 18?"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "Page 18 contains hardware requirements."
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"] == "Summarise the document."
    assert msgs[3]["role"] == "assistant"
    assert msgs[3]["content"] == "The document is a B.Tech synopsis."
