import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.gateway import AIGateway
from google.genai.errors import APIError

@pytest.fixture
def mock_settings():
    with patch("app.ai.gateway.settings") as mock:
        mock.groq_api_key = "test_groq_key"
        mock.gemini_api_key = "test_gemini_key"
        mock.groq_model = "test_groq_model"
        mock.gemini_chat_model = "test_gemini_model"
        mock.gemini_fallback_model = "test_fallback_model"
        yield mock

@pytest.fixture
def gateway(mock_settings):
    return AIGateway()

@pytest.mark.asyncio
async def test_groq_success(gateway):
    # Setup mock Groq response
    messages = [{"role": "user", "content": "Hello"}]
    
    async def mock_groq_stream():
        yield {"content": "Hello", "model": "test_groq_model", "provider": "groq"}
        
    with patch.object(gateway, "_stream_groq", return_value=mock_groq_stream()) as mock_groq:
        results = [chunk async for chunk in gateway.stream_chat(messages)]
        assert len(results) == 1
        assert results[0]["provider"] == "groq"
        assert results[0]["content"] == "Hello"

@pytest.mark.asyncio
async def test_groq_unavailable_fallback_gemini(gateway):
    messages = [{"role": "user", "content": "Hello"}]
    
    async def mock_groq_stream():
        raise Exception("Groq is down")
        yield {} # unreachable
        
    async def mock_gemini_stream(messages, model=None):
        yield {"content": "Gemini response", "model": model, "provider": "gemini"}

    with patch.object(gateway, "_stream_groq", return_value=mock_groq_stream()):
        with patch.object(gateway, "_stream_gemini", side_effect=mock_gemini_stream) as mock_gemini:
            results = [chunk async for chunk in gateway.stream_chat(messages)]
            assert len(results) == 1
            assert results[0]["provider"] == "gemini"
            assert results[0]["content"] == "Gemini response"
            mock_gemini.assert_called_once()

@pytest.mark.asyncio
async def test_gemini_persistent_503_secondary_fallback(gateway):
    messages = [{"role": "user", "content": "Hello"}]
    
    # Disable groq to force gemini
    gateway.groq_api_key = None
    
    # Track calls to _stream_gemini
    call_models = []
    
    async def mock_gemini_stream(messages, model=None):
        call_models.append(model)
        if model == "test_gemini_model":
            raise APIError("503 Service Unavailable", code=503)
            yield {}
        else:
            # Secondary fallback succeeds
            yield {"content": "Secondary response", "model": model, "provider": "gemini"}

    with patch.object(gateway, "_stream_gemini", side_effect=mock_gemini_stream):
        results = [chunk async for chunk in gateway.stream_chat(messages)]
        assert len(results) == 1
        assert results[0]["model"] == "test_fallback_model"
        assert results[0]["content"] == "Secondary response"
        assert call_models == ["test_gemini_model", "test_fallback_model"]

@pytest.mark.asyncio
async def test_all_providers_unavailable(gateway):
    messages = [{"role": "user", "content": "Hello"}]
    gateway.groq_api_key = None
    
    async def mock_gemini_stream(messages, model=None):
        raise Exception("Total failure")
        yield {}

    with patch.object(gateway, "_stream_gemini", side_effect=mock_gemini_stream):
        with pytest.raises(RuntimeError, match="No LLM providers available"):
            [chunk async for chunk in gateway.stream_chat(messages)]
