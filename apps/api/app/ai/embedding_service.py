"""
DocuMind AI — Embedding Service (Gemini Embedding API).

Replaces the sentence-transformers / PyTorch local embedding model with the
Google Gemini Embedding API. This eliminates the ~300-400 MB PyTorch RSS spike
that caused OOM kills on Render's 512 MB free tier.

Model: gemini-embedding-004
Vector dimension: 768  (BREAKING CHANGE from 384 — Qdrant collection must be recreated)
Task type: RETRIEVAL_DOCUMENT for document chunks, RETRIEVAL_QUERY for search queries.

Rate limits (free tier): 1500 RPM, 100 RPD per model.
Batching: up to 250 chunks per batch call via batch_embed_contents.

Requirements:
  - GEMINI_API_KEY must be set (already required by vision enrichment service)
  - google-genai >= 0.1.0 (already in requirements.txt)
"""

from __future__ import annotations

import logging
import time

from app.ai.models import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini embedding model to use.
# gemini-embedding-2 is the official production model.
# We explicitly specify output_dimensionality=768 to match Qdrant configuration.
GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"

# Maximum texts per batch_embed_contents call (Gemini API limit: 250).
GEMINI_BATCH_LIMIT = 100  # conservative — keeps response size manageable


class EmbeddingService:
    """
    Embedding service backed by the Gemini Embedding API.

    Zero local RAM footprint — embeddings are generated via HTTPS call.
    Falls back gracefully with RuntimeError if GEMINI_API_KEY is not set.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.model_name = GEMINI_EMBEDDING_MODEL
        self.batch_size = GEMINI_BATCH_LIMIT
        self._client = None

    def _get_client(self):
        """Lazily initialise the Gemini client on the v1 API endpoint.

        The google-genai SDK defaults to v1beta, where embedding models are
        NOT available (returns 404). Forcing api_version='v1' is required.
        """
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Embedding service cannot initialise. "
                    "Set GEMINI_API_KEY in Render environment variables."
                )
            try:
                from google import genai
                self._client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options={"api_version": "v1"},
                )
                logger.info(f"[EMBEDDING] Gemini client initialised model={self.model_name} api_version=v1")
            except Exception as exc:
                logger.error(f"[EMBEDDING] Failed to initialise Gemini client: {exc}")
                raise RuntimeError(f"Failed to initialise Gemini embedding client: {exc}") from exc
        return self._client

    def embed(self, chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
        """
        Embeds a list of Chunks using the Gemini Embedding API.

        Returns a list of (Chunk, embedding_vector) tuples.
        Vectors are L2-normalised (Gemini returns normalised vectors for RETRIEVAL_DOCUMENT).
        """
        if not chunks:
            return []

        from google.genai import types as genai_types

        client = self._get_client()
        result: list[tuple[Chunk, list[float]]] = []

        # Process in batches to respect API limits.
        for batch_start in range(0, len(chunks), self.batch_size):
            batch = chunks[batch_start: batch_start + self.batch_size]
            texts = [chunk.content for chunk in batch]

            logger.info(
                f"[EMBEDDING] batch started "
                f"batch_start={batch_start} batch_size={len(batch)}"
            )

            retries = 3
            backoff = 2.0
            last_exc = None

            for attempt in range(retries):
                try:
                    response = client.models.embed_content(
                        model=self.model_name,
                        contents=texts,
                        config=genai_types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            output_dimensionality=768,
                        ),
                    )
                    embeddings = response.embeddings
                    if not embeddings:
                        raise RuntimeError("Gemini returned no embeddings")
                    if len(embeddings) != len(batch):
                        raise RuntimeError(
                            f"Gemini returned {len(embeddings)} embeddings for {len(batch)} texts."
                        )

                    logger.info(
                        f"[EMBEDDING] model={self.model_name} requested_dimension=768 batch_size={len(batch)}"
                    )

                    for chunk, emb in zip(batch, embeddings, strict=True):
                        vector = emb.values
                        if not vector:
                            raise RuntimeError(
                                f"Gemini returned empty embedding for chunk {chunk.chunk_id}"
                            )
                        if len(vector) != 768:
                            raise RuntimeError(
                                f"Invalid embedding dimension: {len(vector)}, expected 768"
                            )
                        result.append((chunk, list(vector)))

                    logger.info("[EMBEDDING] dimension_validation=passed")
                    logger.info(
                        f"[EMBEDDING] batch_completed vectors={len(batch)}"
                    )
                    last_exc = None
                    break

                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        f"[EMBEDDING] batch attempt {attempt + 1}/{retries} failed: {exc}"
                    )
                    if attempt < retries - 1:
                        time.sleep(backoff)
                        backoff *= 2

            if last_exc is not None:
                logger.error(f"[EMBEDDING] batch permanently failed: {last_exc}")
                raise RuntimeError(
                    f"Embedding generation failed after {retries} attempts: {last_exc}"
                ) from last_exc

        return result

    def embed_query(self, text: str) -> list[float]:
        """
        Embeds a single query string for semantic search.
        Uses RETRIEVAL_QUERY task type for optimised retrieval performance.
        """
        from google.genai import types as genai_types

        client = self._get_client()

        retries = 3
        backoff = 2.0
        last_exc = None

        for attempt in range(retries):
            try:
                response = client.models.embed_content(
                    model=self.model_name,
                    contents=[text],
                    config=genai_types.EmbedContentConfig(
                        task_type="RETRIEVAL_QUERY",
                        output_dimensionality=768,
                    ),
                )
                vector = response.embeddings[0].values
                if not vector:
                    raise RuntimeError("Gemini returned empty query embedding.")
                if len(vector) != 768:
                    raise RuntimeError(f"Invalid embedding dimension: {len(vector)}, expected 768")
                return list(vector)

            except Exception as exc:
                last_exc = exc
                logger.warning(f"[EMBEDDING] query attempt {attempt + 1}/{retries} failed: {exc}")
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2

        raise RuntimeError(
            f"Query embedding failed after {retries} attempts: {last_exc}"
        ) from last_exc
