"""
DocuMind AI — Chat API endpoint tests.

Verifies:
- Conversation creation/retrieval with the correct auth dependency path.
- dependency_overrides are cleaned up after each test (pytest autouse fixture).
- Unauthorized conversation access returns 404 to avoid resource enumeration.
- Unauthenticated requests are rejected.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app)

# Use a valid UUID string for user_id because ConversationResponse.user_id is uuid.UUID
TEST_USER = str(uuid.uuid4())
OTHER_USER = str(uuid.uuid4())

CONVO_STUB = {
    "id": None,  # filled in per-test
    "user_id": TEST_USER,
    "title": "Test Convo",
    "document_id": None,
    "created_at": "2026-08-16T00:00:00Z",
    "updated_at": "2026-08-16T00:00:00Z",
}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleaned up after every test to
    prevent state leaking into subsequent tests (which caused auth test
    failures when run in the full suite)."""
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _override_user(user_id: str = TEST_USER):
    app.dependency_overrides[get_current_user] = lambda: user_id


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_create_conversation(mock_convo_repo):
    _override_user()
    convo_id = str(uuid.uuid4())
    stub = {**CONVO_STUB, "id": convo_id}
    mock_convo_repo.create_conversation.return_value = stub

    response = client.post(
        "/api/v1/conversations",
        json={"title": "Test Convo"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == convo_id
    assert data["user_id"] == TEST_USER
    # messages list must be initialised to []
    assert data["messages"] == []


@patch("app.api.v1.endpoints.chat.message_repository")
@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_get_conversation(mock_convo_repo, mock_message_repo):
    _override_user()
    convo_id = uuid.uuid4()
    stub = {**CONVO_STUB, "id": str(convo_id)}
    mock_convo_repo.get_conversation_by_id.return_value = stub
    mock_message_repo.list_messages_for_conversation.return_value = []

    response = client.get(f"/api/v1/conversations/{convo_id}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Test Convo"
    assert data["messages"] == []
    # Verify the authenticated user_id was forwarded to the repository —
    # not any user_id supplied by the client.
    mock_convo_repo.get_conversation_by_id.assert_called_once_with(convo_id, TEST_USER)


@patch("app.api.v1.endpoints.chat.conversation_repository")
def test_get_conversation_not_found_returns_404(mock_convo_repo):
    """
    SECURITY: When a conversation belongs to another user the repository
    returns None (it filters by user_id). The endpoint must return 404 —
    not 403 — to avoid revealing that the resource exists (resource
    enumeration prevention).
    """
    _override_user()
    convo_id = uuid.uuid4()
    mock_convo_repo.get_conversation_by_id.return_value = None

    response = client.get(f"/api/v1/conversations/{convo_id}")

    assert response.status_code == 404


def test_conversation_requires_auth():
    """Endpoint must reject requests with no credentials."""
    response = client.get(f"/api/v1/conversations/{uuid.uuid4()}")
    # FastAPI HTTPBearer returns 403 when auto_error=True and no auth header
    # In some FastAPI versions this is 401 — accept either rejection code.
    assert response.status_code in (401, 403)


def test_list_conversations_requires_auth():
    response = client.get("/api/v1/conversations")
    assert response.status_code in (401, 403)
