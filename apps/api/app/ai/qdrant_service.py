import logging
from typing import List, Tuple

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:
    pass

from app.core.config import settings
from app.ai.models import Chunk

logger = logging.getLogger(__name__)


class QdrantService:
    COLLECTION_NAME = "document_chunks"
    VECTOR_SIZE = 384

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
        if not self.client:
            return

        try:
            if not self.client.collection_exists(self.COLLECTION_NAME):
                logger.info(f"Creating Qdrant collection: {self.COLLECTION_NAME}")
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=qmodels.VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=qmodels.Distance.COSINE,
                        on_disk=True
                    )
                )

                # Create payload indexes
                for field in ["user_id", "document_id", "chunk_type"]:
                    self.client.create_payload_index(
                        collection_name=self.COLLECTION_NAME,
                        field_name=field,
                        field_schema=qmodels.PayloadSchemaType.KEYWORD
                    )
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            raise

    def upsert(self, chunks_with_vectors: List[Tuple[Chunk, List[float]]], user_id: str):
        self._initialize()
        if not user_id:
            raise ValueError("user_id is mandatory for Qdrant upsert to enforce isolation.")

        if not chunks_with_vectors or not self.client:
            return

        points = []
        for chunk, vector in chunks_with_vectors:
            if chunk.user_id != user_id:
                raise ValueError("Mismatch between chunk user_id and provided user_id")

            payload = {
                "user_id": user_id,
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "chunk_type": chunk.chunk_type,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section_path": chunk.section_path,
                "content_preview": chunk.content_preview
            }

            points.append(
                qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points
        )

    def delete_by_document(self, document_id: str, user_id: str):
        """
        Deletes all chunks for a given document. Must supply user_id to enforce isolation.
        """
        self._initialize()
        if not user_id:
            raise ValueError("user_id is mandatory for Qdrant delete to enforce isolation.")

        if not self.client:
            return

        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value=user_id)),
                    qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))
                ]
            )
        )
