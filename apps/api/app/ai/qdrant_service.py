"""
DocuMind AI — Qdrant Vector Store Service.

Collection: document_chunks
Vector: single unnamed dense vector, 768 dimensions, COSINE distance
Model: gemini-embedding-2

On initialization the service validates that the existing collection
matches the required schema.  If it does not (wrong dimension, named
vectors, etc.), the collection is deleted and cleanly recreated.

Payload indexes are created for user_id and document_id because these
fields are used in every filter (multi-tenant isolation + per-document
cleanup/search).
"""

import logging
import threading

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:
    QdrantClient = None  # type: ignore[misc]
    qmodels = None  # type: ignore[assignment]

from app.ai.models import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread lock so only one thread performs collection init.
_init_lock = threading.Lock()


class QdrantService:
    COLLECTION_NAME = "document_chunks"
    VECTOR_SIZE = 768  # gemini-embedding-2

    def __init__(self):
        self.client: QdrantClient | None = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize(self):
        """Thread-safe lazy initialization of Qdrant client + collection."""
        if self._initialized:
            return

        with _init_lock:
            # Double-check after acquiring lock.
            if self._initialized:
                return

            url = settings.qdrant_url
            api_key = settings.qdrant_api_key

            kwargs: dict = {"url": url}
            if api_key:
                kwargs["api_key"] = api_key

            try:
                self.client = QdrantClient(**kwargs)
                self._ensure_collection()
                self._initialized = True
                logger.info(
                    f"[QDRANT] initialization=ready "
                    f"collection={self.COLLECTION_NAME} "
                    f"vector_dimension={self.VECTOR_SIZE} "
                    f"vector_mode=unnamed distance=Cosine"
                )
            except Exception as e:
                logger.error(
                    f"[QDRANT] initialization_failed error={e}",
                    exc_info=True,
                )
                self.client = None
                raise

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def _ensure_collection(self):
        """Ensure collection exists with correct unnamed-vector schema.

        Detects and handles:
        - Collection does not exist → create it.
        - Collection exists with wrong dimension → delete + recreate.
        - Collection exists with named vectors → delete + recreate.
        - Collection exists and is correct → validate indexes.
        """
        if not self.client:
            return

        if not self.client.collection_exists(self.COLLECTION_NAME):
            logger.info(
                f"[QDRANT] collection_not_found "
                f"collection={self.COLLECTION_NAME}"
            )
            self._create_collection()
            return

        # Collection exists — inspect its schema.
        info = self.client.get_collection(self.COLLECTION_NAME)
        vectors_config = info.config.params.vectors

        logger.info(
            f"[QDRANT] checking collection={self.COLLECTION_NAME} "
            f"existing_schema_type={type(vectors_config).__name__}"
        )

        # Determine whether schema is correct.
        needs_recreate = False
        reason = ""

        if isinstance(vectors_config, qmodels.VectorParams):
            # Single unnamed vector — this is what we want.
            actual_dim = vectors_config.size
            logger.info(
                f"[QDRANT] expected_dimension={self.VECTOR_SIZE} "
                f"actual_dimension={actual_dim}"
            )
            if actual_dim != self.VECTOR_SIZE:
                needs_recreate = True
                reason = (
                    f"dimension_mismatch "
                    f"expected={self.VECTOR_SIZE} "
                    f"actual={actual_dim}"
                )
        elif isinstance(vectors_config, dict):
            # Named vectors — we need unnamed.  Always recreate.
            needs_recreate = True
            reason = (
                f"named_vectors_detected "
                f"keys={list(vectors_config.keys())}"
            )
        else:
            # Unknown config type — recreate to be safe.
            needs_recreate = True
            reason = (
                f"unknown_config_type={type(vectors_config).__name__}"
            )

        if needs_recreate:
            logger.warning(
                f"[QDRANT] schema_mismatch_detected "
                f"reason={reason} — recreating collection"
            )
            self.client.delete_collection(self.COLLECTION_NAME)
            self._create_collection()
        else:
            logger.info("[QDRANT] dimension_validation=passed")
            # Ensure payload indexes exist even for pre-existing
            # collections (idempotent operation).
            self._ensure_payload_indexes()

    def _create_collection(self):
        """Create document_chunks with a single unnamed 768-dim vector."""
        logger.info(
            f"[QDRANT] creating collection={self.COLLECTION_NAME} "
            f"dimension={self.VECTOR_SIZE} distance=COSINE "
            f"vector_mode=unnamed"
        )
        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=self.VECTOR_SIZE,
                distance=qmodels.Distance.COSINE,
            ),
        )
        self._ensure_payload_indexes()
        logger.info(
            f"[QDRANT] collection_created "
            f"collection={self.COLLECTION_NAME} "
            f"dimension={self.VECTOR_SIZE}"
        )

    def _ensure_payload_indexes(self):
        """Create payload indexes for fields used in filters.

        Qdrant requires an index on any field used in a filter.
        create_payload_index is idempotent — safe to call even if
        the index already exists.
        """
        for field in ["user_id", "document_id"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
            except Exception:
                # Already exists — ignore.
                pass

        try:
            self.client.create_payload_index(
                collection_name=self.COLLECTION_NAME,
                field_name="page_number",
                field_schema=qmodels.PayloadSchemaType.INTEGER,
            )
        except Exception:
            # Already exists — ignore.
            pass

        logger.info(
            f"[QDRANT] user_id_index=ready "
            f"document_id_index=ready "
            f"page_number_index=ready"
        )

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert(
        self,
        chunks_with_vectors: list[tuple[Chunk, list[float]]],
        user_id: str,
    ):
        """Upsert chunk vectors into Qdrant.

        Each PointStruct uses an unnamed vector (plain list[float]).
        """
        self._initialize()
        if not user_id:
            raise ValueError(
                "user_id is mandatory for Qdrant upsert."
            )
        if not chunks_with_vectors or not self.client:
            return

        # Pre-validate every vector dimension.
        for chunk, vector in chunks_with_vectors:
            if len(vector) != self.VECTOR_SIZE:
                raise ValueError(
                    f"Expected embedding dimension "
                    f"{self.VECTOR_SIZE}, got {len(vector)} "
                    f"for chunk {chunk.chunk_id}"
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

            # Unnamed vector: vector=list[float], NOT vector={"name": [...]}
            points.append(
                qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=payload,
                )
            )

        # Batch upsert to prevent timeouts on large documents
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i: i + batch_size]
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=batch,
            )

        logger.info(
            f"[QDRANT] upsert_completed "
            f"points={len(points)} user_id={user_id}"
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_by_document(self, document_id: str, user_id: str):
        """Delete all points for a document.

        Both user_id and document_id are used in the filter — both
        have KEYWORD payload indexes created during initialization.
        """
        self._initialize()
        if not user_id:
            raise ValueError(
                "user_id is mandatory for Qdrant delete."
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
                            value=document_id,
                        ),
                    ),
                ]
            ),
        )
