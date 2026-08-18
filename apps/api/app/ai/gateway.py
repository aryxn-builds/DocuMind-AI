import logging
from collections.abc import AsyncGenerator
from typing import Any

try:
    from groq import APIStatusError as GroqAPIStatusError
except ImportError:
    GroqAPIStatusError = Exception  # fallback if groq not installed

from app.ai.tracer import observe
from app.core.config import settings

logger = logging.getLogger(__name__)

# Groq HTTP status codes that indicate the REQUEST itself is invalid.
# These must NOT trigger a Gemini fallback — the problem is on our side.
_GROQ_NO_RETRY_STATUS = {400, 401, 403, 422}


class AIGateway:
    """
    Provider-agnostic AI Gateway.
    Routes requests to Groq (primary) or Gemini (fallback) and streams responses.
    Only network / 5xx / timeout failures trigger the fallback — 4xx client
    errors are re-raised immediately so the caller gets a clear error instead
    of a misleading Gemini-generated response.
    """
    
    # Class-level cache to permanently disable Groq if we hit a 404 model_not_found
    # to avoid wasting 1+ seconds on every request
    _groq_permanently_failed = False

    def __init__(self):
        self.groq_api_key = settings.groq_api_key
        self.gemini_api_key = settings.gemini_api_key

        self.groq_client = None
        self.gemini_client = None

        self.groq_model = settings.groq_model
        self.gemini_model = settings.gemini_chat_model

    @observe(name="ai_gateway.stream_chat", capture_input=False, capture_output=False)
    async def stream_chat(self, messages: list[dict[str, Any]]) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streams a chat completion using the primary provider, falling back to Gemini
        only on network / server-side failures — not on 4xx client errors.
        Yields dictionaries with {"content": str, "model": str, "provider": str}.
        """
        if self.groq_api_key and not self.__class__._groq_permanently_failed:
            try:
                logger.info("Attempting primary LLM provider (Groq)")
                async for chunk in self._stream_groq(messages):
                    yield chunk
                return
            except GroqAPIStatusError as e:
                status_code = getattr(e, 'status_code', 500)
                if status_code == 404:
                    logger.error(f"Groq rejected request (404 model not found). Disabling Groq for future requests: {e}")
                    self.__class__._groq_permanently_failed = True
                elif status_code in _GROQ_NO_RETRY_STATUS:
                    logger.error(f"Groq rejected request ({status_code}): {e}")
                    raise
                else:
                    logger.error(f"Groq server/network error, attempting Gemini fallback: {e}")
            except Exception as e:
                logger.error(f"Groq unexpected error, attempting Gemini fallback: {e}")

        if self.gemini_api_key:
            logger.info(f"Attempting fallback LLM provider (Gemini: {self.gemini_model})")
            try:
                async for chunk in self._stream_gemini(messages, model=self.gemini_model):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"Primary Gemini model ({self.gemini_model}) failed: {e}")
                
                gemini_fallback = getattr(settings, 'gemini_fallback_model', None)
                if gemini_fallback and gemini_fallback != self.gemini_model:
                    logger.info(f"Attempting secondary LLM provider (Gemini fallback: {gemini_fallback})")
                    try:
                        async for chunk in self._stream_gemini(messages, model=gemini_fallback):
                            yield chunk
                        return
                    except Exception as secondary_err:
                        logger.error(f"Secondary Gemini fallback ({gemini_fallback}) also failed: {secondary_err}")

        raise RuntimeError("No LLM providers available or all providers failed.")

    async def _stream_groq(self, messages: list[dict[str, Any]]) -> AsyncGenerator[dict[str, Any], None]:
        import groq
        if not self.groq_client:
            self.groq_client = groq.AsyncGroq(api_key=self.groq_api_key)
        stream = await self.groq_client.chat.completions.create(
            messages=messages,
            model=self.groq_model,
            temperature=0.1,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield {
                    "content": content,
                    "model": self.groq_model,
                    "provider": "groq"
                }

    async def _stream_gemini(self, messages: list[dict[str, Any]], model: str = None) -> AsyncGenerator[dict[str, Any], None]:
        import asyncio
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError

        if not self.gemini_client:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)

        use_model = model or self.gemini_model
        gemini_messages = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [{"text": msg["content"]}]})

        max_attempts = 3
        base_delay = 2

        for attempt in range(max_attempts):
            try:
                response = await self.gemini_client.aio.models.generate_content_stream(
                    model=use_model,
                    contents=gemini_messages,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        automatic_function_calling={"disable": True}
                    )
                )

                # Fetch first chunk to catch 503/429 connection errors early before yielding
                iterator = response.__aiter__()
                first_chunk = await iterator.__anext__()
                
                if first_chunk.text:
                    yield {
                        "content": first_chunk.text,
                        "model": use_model,
                        "provider": "gemini"
                    }

                async for chunk in iterator:
                    if chunk.text:
                        yield {
                            "content": chunk.text,
                            "model": use_model,
                            "provider": "gemini"
                        }
                return  # Successful completion

            except APIError as e:
                if getattr(e, 'code', 500) in (429, 500, 503) and attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Gemini error {getattr(e, 'code', 500)} ({getattr(e, 'message', str(e))}). Retrying in {delay}s... (Attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(delay)
                else:
                    raise


gateway = AIGateway()
