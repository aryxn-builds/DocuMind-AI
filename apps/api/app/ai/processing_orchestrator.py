import logging
import asyncio

from app.core.config import settings
from app.repositories import job_repository, chunk_repository, document_repository
from app.services import storage_service
from app.ai.adapters.factory import get_adapter
from app.ai.vision_service import VisionEnrichmentService
from app.ai.chunker import Chunker
from app.ai.embedding_service import EmbeddingService
from app.ai.qdrant_service import QdrantService
from app.ai.tracer import observe

logger = logging.getLogger(__name__)

_semaphore = asyncio.Semaphore(settings.concurrent_processing_limit)


class ProcessingOrchestrator:
    def __init__(self):
        self.vision_service = VisionEnrichmentService()
        self.chunker = Chunker()
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    async def run(self, job_id: str, document_id: str, user_id: str):
        """Runs the processing pipeline within a concurrency-limited semaphore."""
        async with _semaphore:
            await asyncio.to_thread(self._run_sync, job_id, document_id, user_id)

    @observe(as_type="generation", name="Process Document")
    def _run_sync(self, job_id: str, document_id: str, user_id: str):
        job = job_repository.claim_job(job_id)
        if not job:
            logger.info(f"Job {job_id} could not be claimed (already processing/failed/completed).")
            return

        document_repository.update_document_status(document_id, user_id, "processing")
        
        try:
            logger.info(f"Running idempotent cleanup for document {document_id}")
            self.qdrant_service.delete_by_document(document_id, user_id)
            chunk_repository.delete_by_document(document_id, user_id)
            
            doc = document_repository.get_document(document_id, user_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found.")

            file_path = doc["file_path"]
            mime_type = doc["mime_type"]
            title = doc["title"]
            
            job_repository.update_job_progress(job_id, 0.1, "downloading")
            
            file_bytes = storage_service.download_document(file_path)
            if not file_bytes:
                raise RuntimeError("Empty file downloaded.")
                
            job_repository.update_job_progress(job_id, 0.2, "parsing")
            
            adapter = get_adapter(document_id, user_id, file_path, mime_type, title)
            normalized_doc = adapter.parse(file_bytes)
            
            document_repository.update_document_metadata(document_id, user_id, {"page_count": normalized_doc.page_count, "processing_metadata": normalized_doc.processing_metadata})
            
            if normalized_doc.page_count > settings.max_pages:
                raise ValueError(f"Document exceeds max page limit ({normalized_doc.page_count} > {settings.max_pages})")
                
            job_repository.update_job_progress(job_id, 0.4, "enriching")
            
            normalized_doc = self.vision_service.enrich(normalized_doc)
            
            job_repository.update_job_progress(job_id, 0.6, "chunking")
            
            chunks = self.chunker.chunk(normalized_doc)
            if not chunks:
                raise ValueError("No processable content found in document.")
                
            job_repository.update_job_progress(job_id, 0.7, "embedding")
            
            chunks_with_vectors = self.embedding_service.embed(chunks)
            
            job_repository.update_job_progress(job_id, 0.8, "indexing")
            
            # CONSISTENCY PROTOCOL: Qdrant first, PostgreSQL second, Rollback on failure.
            try:
                self.qdrant_service.upsert(chunks_with_vectors, user_id)
            except Exception as e:
                logger.error(f"Qdrant indexing failed for {document_id}: {e}")
                raise RuntimeError("Failed to index vectors in Qdrant") from e
                
            try:
                chunk_repository.insert_chunks(chunks)
            except Exception as e:
                logger.error(f"PostgreSQL chunk metadata insert failed for {document_id}: {e}")
                # Rollback Qdrant points
                try:
                    self.qdrant_service.delete_by_document(document_id, user_id)
                except Exception as rollback_e:
                    logger.critical(f"Failed to rollback Qdrant vectors after PG failure for {document_id}: {rollback_e}")
                raise RuntimeError("Failed to insert chunk metadata in PostgreSQL") from e

            job_repository.complete_job(job_id)
            document_repository.update_document_status(document_id, user_id, "ready")
            
            logger.info(f"Successfully processed document {document_id}")

        except Exception as e:
            logger.error(f"Processing failed for job {job_id}: {e}", exc_info=True)
            job_repository.fail_job(job_id, stage="processing", message=str(e), retry_count=0)
            document_repository.update_document_status(document_id, user_id, "failed")
