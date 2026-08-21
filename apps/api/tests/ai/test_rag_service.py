import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.chat import RagRequest, SearchResult, SearchResponse
from app.services.rag_service import rag_service

@pytest.fixture
def mock_dependencies():
    with patch("app.services.rag_service.conversation_repository") as mock_convo_repo, \
         patch("app.services.rag_service.message_repository") as mock_msg_repo, \
         patch("app.services.rag_service.retrieval_service") as mock_retrieval, \
         patch("app.services.rag_service.document_repository") as mock_doc_repo, \
         patch("app.services.rag_service.gateway") as mock_gateway, \
         patch("app.services.rag_service.chunk_repository") as mock_chunk_repo, \
         patch("app.services.rag_service.citation_repository") as mock_cit_repo:
        
        yield {
            "convo_repo": mock_convo_repo,
            "msg_repo": mock_msg_repo,
            "retrieval": mock_retrieval,
            "doc_repo": mock_doc_repo,
            "gateway": mock_gateway,
            "chunk_repo": mock_chunk_repo,
            "cit_repo": mock_cit_repo
        }

@pytest.mark.asyncio
async def test_rag_service_intent_broad_query(mock_dependencies):
    user_id = "test_user"
    conversation_id = uuid.uuid4()
    request = RagRequest(query="Please summarize this entire document", answer_depth="high")

    mock_dependencies["convo_repo"].get_conversation_by_id.return_value = {"id": conversation_id, "document_id": None}
    mock_dependencies["msg_repo"].create_message.return_value = {"id": uuid.uuid4()}
    mock_dependencies["msg_repo"].list_messages_for_conversation.return_value = []
    
    mock_dependencies["retrieval"].search.return_value = SearchResponse(results=[], query_time_ms=10.0)
    
    async def mock_stream_gen():
        yield {"provider": "test", "model": "test", "content": "Here is the summary."}
    
    mock_dependencies["gateway"].stream_chat.return_value = mock_stream_gen()
    
    # Run
    async for _ in rag_service.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)}):
        pass

    # Assert search was called with top_k=30 because of "summarize" and "entire document"
    search_call_args = mock_dependencies["retrieval"].search.call_args[0]
    search_request = search_call_args[1]
    assert search_request.top_k == 30

@pytest.mark.asyncio
async def test_rag_service_intent_specific_query(mock_dependencies):
    user_id = "test_user"
    conversation_id = uuid.uuid4()
    request = RagRequest(query="What is the total revenue in Q3?", answer_depth="medium")

    mock_dependencies["convo_repo"].get_conversation_by_id.return_value = {"id": conversation_id, "document_id": None}
    mock_dependencies["msg_repo"].create_message.return_value = {"id": uuid.uuid4()}
    mock_dependencies["msg_repo"].list_messages_for_conversation.return_value = []
    
    mock_dependencies["retrieval"].search.return_value = SearchResponse(results=[], query_time_ms=10.0)
    
    async def mock_stream_gen():
        yield {"provider": "test", "model": "test", "content": "Revenue is 500k."}
    
    mock_dependencies["gateway"].stream_chat.return_value = mock_stream_gen()
    
    # Run
    async for _ in rag_service.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)}):
        pass

    # Assert search was called with top_k=7 because it's a specific query
    search_call_args = mock_dependencies["retrieval"].search.call_args[0]
    search_request = search_call_args[1]
    assert search_request.top_k == 7

@pytest.mark.asyncio
async def test_rag_service_citations_1_based_indexing(mock_dependencies):
    user_id = "test_user"
    conversation_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    request = RagRequest(query="Tell me about X", answer_depth="low")

    mock_dependencies["convo_repo"].get_conversation_by_id.return_value = {"id": conversation_id, "document_id": None}
    mock_dependencies["msg_repo"].create_message.return_value = {"id": uuid.uuid4()}
    mock_dependencies["msg_repo"].list_messages_for_conversation.return_value = []
    
    mock_dependencies["doc_repo"].get_document_by_id.return_value = {"title": "report.pdf"}
    
    mock_dependencies["retrieval"].search.return_value = SearchResponse(
        results=[
            SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                chunk_type="text",
                page_number=1,
                content="X is a great feature.",
                relevance_score=0.9
            )
        ],
        query_time_ms=10.0
    )
    
    # The LLM outputs the 1-based citation index
    async def mock_stream_gen():
        yield {"provider": "test", "model": "test", "content": "X is great [Source: 1]."}
    
    mock_dependencies["gateway"].stream_chat.return_value = mock_stream_gen()
    
    mock_dependencies["chunk_repo"].get_chunks_by_ids.return_value = [
        {"id": chunk_id, "document_id": doc_id, "page_number": 1, "content": "X is a great feature."}
    ]
    
    # Run
    outputs = []
    async for chunk in rag_service.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)}):
        outputs.append(chunk)

    # Assert the LLM context had "[Source: 1]" in it
    # We can inspect the arguments passed to gateway.stream_chat
    gateway_call_messages = mock_dependencies["gateway"].stream_chat.call_args[0][0]
    system_prompt = gateway_call_messages[0]["content"]
    assert "[Source: 1] (File: report.pdf | Page: 1)" in system_prompt
    assert str(chunk_id) not in system_prompt  # No raw UUID leaked to LLM
    
    # Assert answer depth text is in prompt
    assert "Provide a concise answer with key points only." in system_prompt

    # Assert citations were parsed correctly
    citations_output = [o for o in outputs if o["type"] == "citations"]
    assert len(citations_output) == 1
    citations_list = citations_output[0]["citations"]
    assert len(citations_list) == 1
    assert citations_list[0]["chunk_id"] == str(chunk_id)
    assert citations_list[0]["filename"] == "report.pdf"

@pytest.mark.asyncio
async def test_rag_service_page_not_found(mock_dependencies):
    user_id = "test_user"
    conversation_id = uuid.uuid4()
    request = RagRequest(query="what is on page 999?", answer_depth="medium")

    mock_dependencies["convo_repo"].get_conversation_by_id.return_value = {"id": conversation_id, "document_id": None}
    mock_dependencies["msg_repo"].create_message.return_value = {"id": uuid.uuid4()}
    mock_dependencies["msg_repo"].list_messages_for_conversation.return_value = []
    
    mock_dependencies["retrieval"].search.return_value = SearchResponse(results=[], query_time_ms=10.0)
    
    # Run
    outputs = []
    async for chunk in rag_service.stream_chat(user_id, conversation_id, request, {"id": str(conversation_id)}):
        outputs.append(chunk)

    # Assert search was called with top_k=15 because of page specific query
    search_call_args = mock_dependencies["retrieval"].search.call_args[0]
    search_request = search_call_args[1]
    assert search_request.top_k == 15
    assert search_request.page_numbers == [999]
    
    assert outputs[0]["content"] == "I couldn't find indexed content for page 999 in this document."
