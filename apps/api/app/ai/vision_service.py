import base64
import logging
import time

from app.ai.models import BlockType, NormalizedDocument
from app.core.config import settings

logger = logging.getLogger(__name__)

class VisionEnrichmentService:
    def __init__(self):
        self.model_name = settings.gemini_vision_model

    def enrich(self, document: NormalizedDocument) -> NormalizedDocument:
        if not settings.gemini_api_key:
            logger.warning("No GEMINI_API_KEY set. Skipping vision enrichment.")
            self._fill_placeholders(document)
            return document

        from google import genai
        from google.genai import types
        import concurrent.futures

        client = genai.Client(api_key=settings.gemini_api_key)

        image_blocks = [b for b in document.blocks if b.block_type == BlockType.IMAGE and b.image_ref]
        
        # Limit the number of concurrent vision calls to avoid breaking budget/rate limits
        blocks_to_process = image_blocks[:settings.max_vision_calls_per_doc]
        blocks_to_skip = image_blocks[settings.max_vision_calls_per_doc:]

        # Mark skipped blocks
        for block in blocks_to_skip:
            block.content = "[Image: visual content, description unavailable due to budget limit]"
            block.image_ref = None

        if not blocks_to_process:
            return document

        def _process_block(block):
            if block.image_ref.startswith("data:"):
                try:
                    mime_part, b64_part = block.image_ref.split(";")
                    _, b64_data = b64_part.split(",")
                    mime_type = mime_part.split(":")[1]

                    image_bytes = base64.b64decode(b64_data)

                    retries = 3
                    backoff = 1
                    success = False

                    for attempt in range(retries):
                        try:
                            response = client.models.generate_content(
                                model=self.model_name,
                                contents=[
                                    "Describe the contents of the attached image in detail. Focus on text, data, charts, and structural diagrams.",
                                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                                ]
                            )
                            page_info = f", Page {block.page_number}" if block.page_number else ""
                            block.content = f"[Image{page_info}]: {response.text}"
                            success = True
                            break
                        except Exception as e:
                            logger.warning(f"Vision API error (attempt {attempt+1}): {e}")
                            if attempt < retries - 1:
                                time.sleep(backoff)
                                backoff *= 2

                    if not success:
                        block.content = "[Image: visual content, description unavailable]"
                except Exception as e:
                    logger.error(f"Failed to process image_ref: {e}")
                    block.content = "[Image: unprocessable format]"
            else:
                block.content = "[Image: unsupported reference format]"

            # Clear image_ref to save memory
            block.image_ref = None

        # Execute vision calls concurrently (max 3 workers to prevent hitting strict free tier RPM/burst limits)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(_process_block, blocks_to_process))

        return document

    def _fill_placeholders(self, document: NormalizedDocument):
        """Fills image blocks with placeholders when vision is disabled."""
        for block in document.blocks:
            if block.block_type == BlockType.IMAGE:
                block.content = "[Image: vision enrichment disabled]"
                block.image_ref = None
