import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.repositories import citation_repository, conversation_repository, message_repository
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    RagRequest,
    SearchRequest,
    SearchResponse,
)
from app.services.rag_service import rag_service
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    request: ConversationCreate,
    user_id: str = Depends(get_current_user)
):
    title = request.title or "New Conversation"

    convo_data = conversation_repository.create_conversation(
        user_id=user_id,
        title=title,
        document_id=request.document_id
    )

    convo_data["messages"] = []
    return convo_data

@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(user_id: str = Depends(get_current_user)):
    convos = conversation_repository.list_conversations(user_id)

    for c in convos:
        c["messages"] = []
    return convos

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: uuid.UUID,
    user_id: str = Depends(get_current_user)
):
    convo = conversation_repository.get_conversation_by_id(conversation_id, user_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_data = message_repository.list_messages_for_conversation(conversation_id, user_id)

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
    user_id: str = Depends(get_current_user)
):
    try:
        return retrieval_service.search(user_id, request)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{conversation_id}/messages")
async def send_message_stream(
    conversation_id: uuid.UUID,
    request: RagRequest,
    user_id: str = Depends(get_current_user)
):
    convo = conversation_repository.get_conversation_by_id(conversation_id, user_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def generate_sse():
        try:
            async for data_item in rag_service.stream_chat(user_id, conversation_id, request):
                data = json.dumps(data_item)
                yield f"data: {data}\n\n"

            # Signal successful completion
            yield "data: [DONE]\n\n"
        except ValueError as e:
            # Authorization / validation failures — report but do not retry
            logger.warning(f"RAG rejected request: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            error_data = json.dumps({"error": "Generation failed. Please try again."})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
