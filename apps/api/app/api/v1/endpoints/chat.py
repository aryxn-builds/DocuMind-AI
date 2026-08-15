import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.repositories import conversation_repository, message_repository, citation_repository
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    SearchRequest,
    SearchResponse,
    RagRequest,
    CitationResponse
)
from app.services.retrieval_service import retrieval_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    request: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    title = request.title or "New Conversation"
    
    convo_data = conversation_repository.create_conversation(
        user_id=user_id,
        title=title,
        document_id=request.document_id
    )
    
    convo_data["messages"] = []
    return convo_data

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    convos = conversation_repository.list_conversations(user_id)
    
    # Optional: fetch messages for each convo if needed, or leave empty
    for c in convos:
        c["messages"] = []
    return convos

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    convo = conversation_repository.get_conversation_by_id(conversation_id, user_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    messages_data = message_repository.list_messages_for_conversation(conversation_id, user_id)
    
    # Fetch citations for assistant messages
    for msg in messages_data:
        msg["citations"] = []
        if msg["role"] == "assistant":
            citations = citation_repository.get_citations_for_message(uuid.UUID(msg["id"]), user_id)
            msg["citations"] = citations
            
    convo["messages"] = messages_data
    return convo

@router.post("/search", response_model=SearchResponse)
def semantic_search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    try:
        return retrieval_service.search(user_id, request)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{conversation_id}/messages")
async def send_message_stream(
    conversation_id: uuid.UUID,
    request: RagRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    
    convo = conversation_repository.get_conversation_by_id(conversation_id, user_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def generate_sse():
        try:
            async for chunk in rag_service.stream_chat(user_id, conversation_id, request):
                # Send raw content chunk
                data = json.dumps({"content": chunk})
                yield f"data: {data}\n\n"
            
            # Send done signal
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
            
    return StreamingResponse(generate_sse(), media_type="text/event-stream")
