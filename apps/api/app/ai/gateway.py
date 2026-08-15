import logging
from typing import AsyncGenerator, Dict, Any, List

try:
    import google.generativeai as genai
except ImportError:
    pass

try:
    import groq
    from groq import APIStatusError as GroqAPIStatusError
except ImportError:
    GroqAPIStatusError = Exception  # fallback if groq not installed

from app.core.config import settings
from app.ai.tracer import observe

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

    def __init__(self):
        self.groq_api_key = settings.groq_api_key
        self.gemini_api_key = settings.gemini_api_key

        if self.groq_api_key:
            self.groq_client = groq.AsyncGroq(api_key=self.groq_api_key)
        else:
            self.groq_client = None

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
        self.groq_model = settings.groq_model
        self.gemini_model = settings.gemini_chat_model

    @observe(name="ai_gateway.stream_chat", capture_input=False, capture_output=False)
    async def stream_chat(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams a chat completion using the primary provider, falling back to Gemini
        only on network / server-side failures — not on 4xx client errors.
        Yields dictionaries with {"content": str, "model": str, "provider": str}.
        """
        if self.groq_client:
            try:
                logger.info("Attempting primary LLM provider (Groq)")
                async for chunk in self._stream_groq(messages):
                    yield chunk
                return
            except GroqAPIStatusError as e:
                if e.status_code in _GROQ_NO_RETRY_STATUS:
                    # Client-side error — re-raise immediately, do NOT fall back
                    logger.error(f"Groq rejected request ({e.status_code}): {e}")
                    raise
                logger.error(f"Groq server/network error ({e.status_code}), attempting Gemini fallback: {e}")
            except Exception as e:
                logger.error(f"Groq unexpected error, attempting Gemini fallback: {e}")

        if self.gemini_api_key:
            logger.info("Attempting fallback LLM provider (Gemini)")
            async for chunk in self._stream_gemini(messages):
                yield chunk
            return

        raise RuntimeError("No LLM providers available or all providers failed.")

    async def _stream_groq(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
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

    async def _stream_gemini(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        gemini_messages = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg["content"]]})

        model_instance = genai.GenerativeModel(
            model_name=self.gemini_model,
            system_instruction=system_instruction
        )

        response = await model_instance.generate_content_async(
            gemini_messages,
            stream=True,
            generation_config=genai.types.GenerationConfig(temperature=0.1)
        )

        async for chunk in response:
            if chunk.text:
                yield {
                    "content": chunk.text,
                    "model": self.gemini_model,
                    "provider": "gemini"
                }


gateway = AIGateway()
