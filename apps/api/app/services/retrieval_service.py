"""
DocuMind AI — Retrieval Service.
"""

from __future__ import annotations

import logging
import time
import uuid

from qdrant_client.http import models as qmodels

from app.ai.embedding_service import EmbeddingService
from app.ai.qdrant_service import QdrantService
from app.schemas.chat import SearchRequest, SearchResponse, SearchResult

logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(self):
        self.qdrant_service = QdrantService()
        self.embedding_service = EmbeddingService()

    def search(self, user_id: str, request: SearchRequest) -> SearchResponse:
        """
        Executes a semantic search against Qdrant.
        Mandatory user_id filter ensures strict multi-tenant isolation.
        """
        start_time = time.time()

        # 1. Embed the query
        query_vector = self.embedding_service.embed_query(request.query)

        # 2. Build filters
        # MUST include user_id to enforce isolation
        must_conditions = [
            qmodels.FieldCondition(
                key="user_id",
                match=qmodels.MatchValue(value=user_id)
            )
        ]

        if request.document_id:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchValue(value=str(request.document_id))
                )
            )

        if request.page_numbers:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="page_number",
                    match=qmodels.MatchAny(any=request.page_numbers)
                )
            )

        search_filter = qmodels.Filter(must=must_conditions)

        # 3. Search Qdrant
        self.qdrant_service._initialize()
        if not self.qdrant_service.client:
            raise RuntimeError("Qdrant client is not available")

        search_response = self.qdrant_service.client.query_points(
            collection_name=self.qdrant_service.COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=request.top_k,
            score_threshold=request.similarity_threshold,
            with_payload=True
        )

        # 4. Normalize results
        results = []
        for scored_point in search_response.points:
            payload = scored_point.payload or {}
            result = SearchResult(
                chunk_id=uuid.UUID(payload.get("chunk_id", str(scored_point.id))),
                document_id=uuid.UUID(payload.get("document_id")),
                chunk_type=payload.get("chunk_type", "text"),
                page_number=payload.get("page_number"),
                content=payload.get("content_preview", ""),
                relevance_score=scored_point.score
            )
            results.append(result)

        query_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=results,
            query_time_ms=query_time_ms
        )

# Singleton instance
retrieval_service = RetrievalService()
