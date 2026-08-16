import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.rag_service import RagService
from app.schemas.chat import RagRequest

@pytest.fixture
def rag_service():
    return RagService()

@pytest.mark.asyncio
@patch('app.services.rag_service.conversation_repository')
@patch('app.services.rag_service.message_repository')
@patch('app.services.rag_service.retrieval_service')
@patch('app.services.rag_service.citation_repository')
@patch('app.services.rag_service.gateway')
async def test_stream_chat_success(
    mock_gateway,
    mock_citation_repo,
    mock_retrieval_service,
    mock_message_repo,
    mock_conversation_repo,
    rag_service
):
    user_id = "test_user_id"
    conversation_id = uuid.uuid4()
    request = RagRequest(query="What is the context?", document_id=uuid.uuid4())
    
    mock_conversation_repo.get_conversation_by_id.return_value = {"id": str(conversation_id)}
    mock_message_repo.create_message.return_value = {"id": str(uuid.uuid4())}
    mock_message_repo.list_messages_for_conversation.return_value = []
    
    mock_search_result = MagicMock()
    mock_search_result.results = []
    mock_retrieval_service.search.return_value = mock_search_result
    
    async def mock_stream(*args, **kwargs):
        yield {"content": "This is the answer.", "model": "test-model", "provider": "test-provider"}
        
    mock_gateway.stream_chat = mock_stream
    
    chunks = []
    async for chunk in rag_service.stream_chat(user_id, conversation_id, request):
        chunks.append(chunk)
        
    assert "".join([c["content"] for c in chunks if c.get("type") == "chunk"]) == "This is the answer."
    mock_conversation_repo.get_conversation_by_id.assert_called_once_with(conversation_id, user_id)
    assert mock_message_repo.create_message.call_count == 2
