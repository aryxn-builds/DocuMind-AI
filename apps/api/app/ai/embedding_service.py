"""
DocuMind AI — Embedding Service (Gemini Embedding API).

Uses the google-genai SDK with gemini-embedding-2 to generate
768-dimensional embeddings via HTTPS. Zero local RAM footprint.

IMPORTANT — Batching:
  When passing multiple texts, each text MUST be wrapped in its own
  types.Content object.  Passing a plain list of strings causes the
  API to concatenate them into ONE content and return ONE embedding.

Model: gemini-embedding-2
Vector dimension: 768  (matches Qdrant VECTOR_SIZE)
Rate limits (free tier): 1500 RPM, 100 RPD per model.

Requirements:
  - GEMINI_API_KEY must be set
  - google-genai >= 0.1.0
"""

from __future__ import annotations

import logging
import time

from app.ai.models import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini embedding model to use.
# gemini-embedding-2 is the official production model.
# We explicitly specify output_dimensionality=768 to match Qdrant.
GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"

# Maximum texts per embed_content call (Gemini API limit: 250).
GEMINI_BATCH_LIMIT = 100  # conservative — keeps response size manageable


class EmbeddingService:
    """
    Embedding service backed by the Gemini Embedding API.

    Zero local RAM footprint — embeddings are generated via HTTPS call.
    Raises RuntimeError if GEMINI_API_KEY is not set.
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

        The google-genai SDK defaults to v1beta, where embedding models
        are NOT available (returns 404). Forcing api_version='v1' is required.
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
                logger.info(
                    "[EMBEDDING] Gemini client initialised "
                    f"model={self.model_name} api_version=v1"
                )
            except Exception as exc:
                logger.error(
                    f"[EMBEDDING] Failed to initialise Gemini client: {exc}"
                )
                raise RuntimeError(
                    f"Failed to initialise Gemini embedding client: {exc}"
                ) from exc
        return self._client

    @staticmethod
    def _build_contents(texts: list[str]):
        """Wrap each text in its own types.Content so the API returns
        one embedding per text.

        Passing a bare list of strings causes gemini-embedding-2 to
        concatenate them into a single content and return only 1 embedding.
        """
        from google.genai import types as genai_types

        return [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=t)],
            )
            for t in texts
        ]

    def embed(self, chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
        """
        Embeds a list of Chunks using the Gemini Embedding API.

        Returns a list of (Chunk, embedding_vector) tuples.
        Each vector has exactly 768 dimensions.
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
                f"[EMBEDDING] model={self.model_name} "
                f"input_texts={len(texts)} batch_start={batch_start}"
            )

            # Build separate Content objects — one per text.
            contents = self._build_contents(texts)

            retries = 3
            backoff = 2.0
            last_exc = None

            for attempt in range(retries):
                try:
                    response = client.models.embed_content(
                        model=self.model_name,
                        contents=contents,
                        config=genai_types.EmbedContentConfig(
                            output_dimensionality=768,
                        ),
                    )

                    embeddings = response.embeddings

                    # --- Validation (fail-fast, no retry) ---
                    if not embeddings:
                        raise RuntimeError(
                            "Gemini returned no embeddings"
                        )

                    if len(embeddings) != len(texts):
                        raise RuntimeError(
                            f"Gemini returned {len(embeddings)} "
                            f"embeddings for {len(texts)} texts"
                        )

                    logger.info(
                        f"[EMBEDDING] returned_embeddings="
                        f"{len(embeddings)}"
                    )

                    for idx, (chunk, emb) in enumerate(
                        zip(batch, embeddings, strict=True)
                    ):
                        vector = emb.values
                        if vector is None:
                            raise RuntimeError(
                                f"Gemini returned empty embedding "
                                f"at index {idx}"
                            )
                        if len(vector) != 768:
                            raise RuntimeError(
                                f"Invalid embedding dimension at "
                                f"index {idx}: {len(vector)}, "
                                f"expected 768"
                            )
                        result.append((chunk, list(vector)))

                    logger.info(
                        f"[EMBEDDING] dimension=768 "
                        f"validation=passed"
                    )
                    logger.info(
                        f"[EMBEDDING] batch_completed "
                        f"vectors={len(batch)}"
                    )
                    last_exc = None
                    break

                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        f"[EMBEDDING] batch attempt "
                        f"{attempt + 1}/{retries} failed: {exc}"
                    )
                    if attempt < retries - 1:
                        time.sleep(backoff)
                        backoff *= 2

            if last_exc is not None:
                logger.error(
                    f"[EMBEDDING] batch permanently failed: "
                    f"{last_exc}"
                )
                raise RuntimeError(
                    f"Embedding generation failed after "
                    f"{retries} attempts: {last_exc}"
                ) from last_exc

        return result

    def embed_query(self, text: str) -> list[float]:
        """
        Embeds a single query string for semantic search.
        Uses a single Content object for one query embedding.
        """
        from google.genai import types as genai_types

        client = self._get_client()

        # Single text → single Content object.
        contents = self._build_contents([text])

        retries = 3
        backoff = 2.0
        last_exc = None

        for attempt in range(retries):
            try:
                response = client.models.embed_content(
                    model=self.model_name,
                    contents=contents,
                    config=genai_types.EmbedContentConfig(
                        output_dimensionality=768,
                    ),
                )
                if not response.embeddings:
                    raise RuntimeError(
                        "Gemini returned no query embeddings"
                    )
                vector = response.embeddings[0].values
                if vector is None:
                    raise RuntimeError(
                        "Gemini returned empty query embedding."
                    )
                if len(vector) != 768:
                    raise RuntimeError(
                        f"Invalid query embedding dimension: "
                        f"{len(vector)}, expected 768"
                    )
                return list(vector)

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    f"[EMBEDDING] query attempt "
                    f"{attempt + 1}/{retries} failed: {exc}"
                )
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2

        raise RuntimeError(
            f"Query embedding failed after {retries} attempts: "
            f"{last_exc}"
        ) from last_exc
