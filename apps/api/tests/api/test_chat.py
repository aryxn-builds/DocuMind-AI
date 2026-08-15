import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import uuid

# Note: assuming app is imported from main
from app.main import app

client = TestClient(app)

@patch('app.api.deps.get_current_user')
@patch('app.api.v1.endpoints.chat.conversation_repository')
def test_create_conversation(mock_convo_repo, mock_get_user):
    mock_get_user.return_value = {"sub": "test_user"}
    mock_convo_repo.create_conversation.return_value = {
        "id": str(uuid.uuid4()),
        "user_id": "test_user",
        "title": "New Conversation",
        "document_id": None,
        "created_at": "2026-08-16T00:00:00Z"
    }
    
    app.dependency_overrides[app.api.deps.get_current_user] = lambda: {"sub": "test_user"}
    
    response = client.post("/api/v1/conversations", json={"title": "Test Convo"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Conversation"

@patch('app.api.deps.get_current_user')
@patch('app.api.v1.endpoints.chat.conversation_repository')
@patch('app.api.v1.endpoints.chat.message_repository')
def test_get_conversation(mock_message_repo, mock_convo_repo, mock_get_user):
    app.dependency_overrides[app.api.deps.get_current_user] = lambda: {"sub": "test_user"}
    
    convo_id = uuid.uuid4()
    mock_convo_repo.get_conversation_by_id.return_value = {
        "id": str(convo_id),
        "user_id": "test_user",
        "title": "Test Convo"
    }
    mock_message_repo.list_messages_for_conversation.return_value = []
    
    response = client.get(f"/api/v1/conversations/{convo_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Convo"
    assert response.json()["messages"] == []
