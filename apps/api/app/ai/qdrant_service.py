"""
DocuMind AI — Qdrant Vector Store Service.

Collection: document_chunks
Vector dimension: 768 (gemini-embedding-2)
Distance: COSINE

On initialization the service validates that any existing collection
has the correct vector dimension.  If the dimension is wrong (e.g. a
stale 384-dimension collection from the old sentence-transformers
model), the collection is deleted and recreated with 768 dimensions.
"""

import logging

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:
    pass

from app.ai.models import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    COLLECTION_NAME = "document_chunks"
    # gemini-embedding-2 produces 768-dimensional vectors.
    VECTOR_SIZE = 768

    def __init__(self):
        self.client = None
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return

        self._initialized = True
        url = settings.qdrant_url
        api_key = settings.qdrant_api_key

        kwargs = {"url": url}
        if api_key:
            kwargs["api_key"] = api_key

        try:
            self.client = QdrantClient(**kwargs)
            self._ensure_collection()
        except Exception as e:
            logger.error(f"Failed to initialize QdrantClient: {e}")
            self.client = None

    def _ensure_collection(self):
        """Ensure the Qdrant collection exists with the correct dimension.

        If the collection exists but has a different vector size (e.g. 384
        from the old sentence-transformers model), it is deleted and
        recreated with the correct 768 dimension.
        """
        if not self.client:
            return

        try:
            if self.client.collection_exists(self.COLLECTION_NAME):
                # --- Validate existing collection dimension ---
                info = self.client.get_collection(self.COLLECTION_NAME)
                vectors_config = info.config.params.vectors

                # vectors_config can be a VectorParams directly
                # or a dict of named vectors.
                if isinstance(vectors_config, qmodels.VectorParams):
                    actual_dim = vectors_config.size
                elif isinstance(vectors_config, dict):
                    # Default unnamed vector
                    default = vectors_config.get("")
                    actual_dim = (
                        default.size if default else None
                    )
                else:
                    actual_dim = None

                logger.info(
                    f"[QDRANT] collection={self.COLLECTION_NAME} "
                    f"expected_dimension={self.VECTOR_SIZE} "
                    f"actual_dimension={actual_dim}"
                )

                if actual_dim is not None and actual_dim != self.VECTOR_SIZE:
                    logger.warning(
                        f"[QDRANT] dimension_mismatch "
                        f"expected={self.VECTOR_SIZE} "
                        f"actual={actual_dim} — "
                        f"deleting and recreating collection"
                    )
                    self.client.delete_collection(self.COLLECTION_NAME)
                    self._create_collection()
                else:
                    logger.info(
                        "[QDRANT] dimension_validation=passed"
                    )
            else:
                self._create_collection()

        except Exception as e:
            logger.error(
                f"Failed to ensure Qdrant collection: {e}"
            )
            raise

    def _create_collection(self):
        """Create the document_chunks collection with 768-dim COSINE vectors."""
        logger.info(
            f"[QDRANT] creating collection={self.COLLECTION_NAME} "
            f"dimension={self.VECTOR_SIZE} distance=COSINE"
        )
        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=self.VECTOR_SIZE,
                distance=qmodels.Distance.COSINE,
                on_disk=True,
            ),
        )

        # Create payload indexes for filtering
        for field in ["user_id", "document_id", "chunk_type"]:
            self.client.create_payload_index(
                collection_name=self.COLLECTION_NAME,
                field_name=field,
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )

        logger.info(
            f"[QDRANT] collection_created "
            f"collection={self.COLLECTION_NAME} "
            f"dimension={self.VECTOR_SIZE}"
        )

    def upsert(
        self,
        chunks_with_vectors: list[tuple[Chunk, list[float]]],
        user_id: str,
    ):
        self._initialize()
        if not user_id:
            raise ValueError(
                "user_id is mandatory for Qdrant upsert "
                "to enforce isolation."
            )

        if not chunks_with_vectors or not self.client:
            return

        # Pre-validate vector dimensions before sending to Qdrant
        for chunk, vector in chunks_with_vectors:
            if len(vector) != self.VECTOR_SIZE:
                raise ValueError(
                    f"Vector dimension mismatch: got {len(vector)}, "
                    f"expected {self.VECTOR_SIZE} for chunk "
                    f"{chunk.chunk_id}"
                )

        points = []
        for chunk, vector in chunks_with_vectors:
            if chunk.user_id != user_id:
                raise ValueError(
                    "Mismatch between chunk user_id and "
                    "provided user_id"
                )

            payload = {
                "user_id": user_id,
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "chunk_type": chunk.chunk_type,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section_path": chunk.section_path,
                "content_preview": chunk.content_preview,
            }

            points.append(
                qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )

    def delete_by_document(self, document_id: str, user_id: str):
        """Delete all chunks for a document (user_id enforces isolation)."""
        self._initialize()
        if not user_id:
            raise ValueError(
                "user_id is mandatory for Qdrant delete "
                "to enforce isolation."
            )

        if not self.client:
            return

        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="user_id",
                        match=qmodels.MatchValue(value=user_id),
                    ),
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(
                            value=document_id
                        ),
                    ),
                ]
            ),
        )
