"""
DocuMind AI — Summarization Service.
Implements hierarchical map-reduce summarization for large documents.
"""

import logging
import uuid
from typing import List

from app.ai.gateway import gateway
from app.ai.models import Chunk, NormalizedDocument

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self):
        # We process chunks in batches of ~15
        self.chunk_batch_size = 15

    async def _generate_summary(self, prompt: str) -> str:
        """Helper to generate a summary using the AIGateway."""
        messages = [{"role": "user", "content": prompt}]
        full_response = ""
        try:
            async for chunk in gateway.stream_chat(messages):
                full_response += chunk["content"]
        except Exception as e:
            logger.error(f"[SUMMARIZATION] LLM generation failed: {e}")
            return ""
        return full_response.strip()

    async def summarize_document(self, document: NormalizedDocument, chunks: List[Chunk]) -> List[Chunk]:
        """
        Takes the standard text chunks of a document, performs a map-reduce
        summarization, and returns a list of summary chunks.
        """
        if not chunks:
            return []

        logger.info(f"[SUMMARIZATION] Starting map-reduce for {len(chunks)} chunks")

        # Map phase: generate section summaries
        section_summaries = []
        for i in range(0, len(chunks), self.chunk_batch_size):
            batch = chunks[i : i + self.chunk_batch_size]
            batch_text = "\n\n".join([f"--- Chunk {c.chunk_index} ---\n{c.content}" for c in batch])
            
            prompt = (
                "You are an expert document summarizer. "
                "Summarize the following section of a document concisely. "
                "Capture the main topics, facts, and key details.\n\n"
                f"{batch_text}"
            )
            
            summary = await self._generate_summary(prompt)
            if summary:
                section_summaries.append(summary)
            
            logger.info(f"[SUMMARIZATION] Map phase progress: {i + len(batch)} / {len(chunks)}")

        if not section_summaries:
            logger.warning("[SUMMARIZATION] Map phase produced no summaries.")
            return []

        # Reduce phase: generate document summary
        reduce_text = "\n\n".join([f"--- Section {idx + 1} Summary ---\n{s}" for idx, s in enumerate(section_summaries)])
        reduce_prompt = (
            "You are an expert document summarizer. "
            "Below are summaries of consecutive sections from a single document. "
            "Synthesize them into a comprehensive, document-wide summary. "
            "Structure it logically, capturing the overall purpose, key methodologies, "
            "and primary conclusions of the entire document.\n\n"
            f"{reduce_text}"
        )
        
        document_summary = await self._generate_summary(reduce_prompt)
        
        summary_chunks = []
        
        # Add the document summary chunk
        if document_summary:
            summary_chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document.document_id,
                    user_id=document.user_id,
                    chunk_index=-1, # negative index to avoid collisions
                    content=document_summary,
                    content_preview=document_summary[:200],
                    chunk_type="document_summary",
                    page_number=1, # conceptually spans the whole document
                    section_path=["Document Summary"]
                )
            )
            
        # Add the section summary chunks
        for idx, s_sum in enumerate(section_summaries):
            summary_chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document.document_id,
                    user_id=document.user_id,
                    chunk_index=-2 - idx,
                    content=s_sum,
                    content_preview=s_sum[:200],
                    chunk_type="section_summary",
                    page_number=1, 
                    section_path=[f"Section Summary {idx + 1}"]
                )
            )

        logger.info(f"[SUMMARIZATION] Map-reduce completed. Generated {len(summary_chunks)} summary chunks.")
        return summary_chunks
