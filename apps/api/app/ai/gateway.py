import logging
import time
from typing import AsyncGenerator, Dict, Any, List

try:
    import google.generativeai as genai
except ImportError:
    pass

try:
    import groq
except ImportError:
    pass

from app.core.config import settings
from app.ai.tracer import observe

logger = logging.getLogger(__name__)

class AIGateway:
    """
    Provider-agnostic AI Gateway.
    Routes requests to Groq (primary) or Gemini (fallback) and streams responses.
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
            self.gemini_model = "gemini-1.5-flash"
        
    @observe(name="ai_gateway.stream_chat", capture_input=False, capture_output=False)
    async def stream_chat(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams a chat completion using the primary provider, falling back to Gemini on failure.
        Yields dictionaries with {"content": str, "model": str, "provider": str}.
        """
        if self.groq_client:
            try:
                # Try Groq first
                logger.info("Attempting primary LLM provider (Groq)")
                async for chunk in await self._stream_groq(messages):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"Primary provider (Groq) failed: {e}")
                
        if self.gemini_api_key:
            # Fallback to Gemini
            logger.info("Attempting fallback LLM provider (Gemini)")
            async for chunk in self._stream_gemini(messages):
                yield chunk
            return
            
        raise RuntimeError("No LLM providers available or all providers failed.")

    async def _stream_groq(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        model = "llama3-8b-8192" # Could be configured via settings, hardcoded for now or use environment
        stream = await self.groq_client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.1,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield {
                    "content": content,
                    "model": model,
                    "provider": "groq"
                }

    async def _stream_gemini(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        # Convert OpenAI format messages to Gemini format
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
        
        # We use sync generate_content with stream=True, but ideally it should be async.
        # Since google-generativeai supports generate_content_async:
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
