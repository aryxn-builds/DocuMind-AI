"""
DocuMind AI — Processing Orchestrator.

Runs the full document ingestion pipeline:
  download → parse → vision-enrich → chunk → embed → upsert-qdrant → pg-chunks → mark-ready

Design notes:
- `_run_sync` is called via `asyncio.to_thread` to keep the event loop unblocked.
- The semaphore is created lazily inside an async context to avoid module-level
  asyncio object creation (deprecated in Python 3.10+).
- Every major stage emits a structured [PROCESSING] log line so Render logs can be
  searched by keyword to find exactly where execution stopped.
- A per-job asyncio.wait_for timeout ensures that even a hung job eventually gets
  marked FAILED rather than stuck in PROCESSING indefinitely.
- A separate `run_orphan_recovery` coroutine is called from main.py on a schedule
  to clean up any jobs that were silently killed (e.g. OOM, SIGKILL).
"""

import asyncio
import logging

from app.ai.adapters.factory import get_adapter
from app.ai.chunker import Chunker
from app.ai.embedding_service import EmbeddingService
from app.ai.qdrant_service import QdrantService
from app.ai.tracer import observe
from app.ai.vision_service import VisionEnrichmentService
from app.core.config import settings
from app.repositories import chunk_repository, document_repository, job_repository
from app.services import storage_service

logger = logging.getLogger(__name__)

# Semaphore is intentionally created lazily inside the event loop (see `_get_semaphore`).
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Returns the module-level semaphore, creating it lazily inside a running loop."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.concurrent_processing_limit)
    return _semaphore


class ProcessingOrchestrator:
    def __init__(self):
        self.vision_service = VisionEnrichmentService()
        self.chunker = Chunker()
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    async def run(self, job_id: str, document_id: str, user_id: str):
        """
        Runs the processing pipeline within a concurrency-limited semaphore.

        Wraps `_run_sync` (synchronous, CPU-bound) via `asyncio.to_thread` so the
        event loop stays responsive during processing. A hard timeout is applied so
        a hung job always ends in FAILED rather than PROCESSING indefinitely.
        """
        timeout = settings.processing_timeout_seconds
        sem = _get_semaphore()

        logger.info(
            f"[PROCESSING] job_queued job_id={job_id} document_id={document_id} timeout={timeout}s"
        )

        async with sem:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._run_sync, job_id, document_id, user_id),
                    timeout=float(timeout),
                )
            except TimeoutError:
                logger.error(
                    f"[PROCESSING] job_timeout job_id={job_id} document_id={document_id} "
                    f"timeout={timeout}s"
                )
                try:
                    job_repository.fail_job(
                        job_id,
                        stage="timeout",
                        message=f"Processing exceeded {timeout}s timeout.",
                        retry_count=0,
                    )
                except Exception as e:
                    logger.error(f"[PROCESSING] failed to mark timed-out job failed: {e}")
                try:
                    document_repository.update_document_status(document_id, user_id, "failed")
                except Exception as e:
                    logger.error(f"[PROCESSING] failed to mark timed-out document failed: {e}")

    @observe(as_type="generation", name="Process Document")
    def _run_sync(self, job_id: str, document_id: str, user_id: str):
        """Synchronous processing pipeline. Runs in a thread pool via asyncio.to_thread."""

        # --- Claim the job atomically (prevents double-processing) ---
        job = job_repository.claim_job(job_id)
        if not job:
            logger.info(
                f"[PROCESSING] job_already_claimed job_id={job_id} — skipping."
            )
            return

        logger.info(f"[PROCESSING] job_started job_id={job_id} document_id={document_id}")
        document_repository.update_document_status(document_id, user_id, "processing")

        try:
            # Idempotent cleanup: remove any prior vectors/chunks from a failed attempt.
            logger.info(f"[PROCESSING] cleanup_started document_id={document_id}")
            self.qdrant_service.delete_by_document(document_id, user_id)
            chunk_repository.delete_by_document(document_id, user_id)
            logger.info(f"[PROCESSING] cleanup_completed document_id={document_id}")

            doc = document_repository.get_document_by_id(document_id, user_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found in database.")

            file_path = doc["file_path"]
            mime_type = doc["file_type"]
            title = doc["title"]

            # --- Stage 1: Download ---
            job_repository.update_job_progress(job_id, 0.05, "downloading")
            logger.info(f"[PROCESSING] download_started document_id={document_id} path={file_path}")
            file_bytes = storage_service.download_document(file_path)
            if not file_bytes:
                raise RuntimeError("Empty file downloaded from storage.")
            logger.info(
                f"[PROCESSING] download_completed document_id={document_id} "
                f"size_bytes={len(file_bytes)}"
            )

            # --- Stage 2: Parse ---
            job_repository.update_job_progress(job_id, 0.15, "parsing")
            logger.info(
                f"[PROCESSING] parse_started document_id={document_id} mime_type={mime_type}"
            )
            adapter = get_adapter(document_id, user_id, file_path, mime_type, title)
            normalized_doc = adapter.parse(file_bytes)
            logger.info(
                f"[PROCESSING] parse_completed document_id={document_id} "
                f"pages={normalized_doc.page_count} blocks={len(normalized_doc.blocks)}"
            )

            document_repository.update_document_metadata(
                document_id,
                user_id,
                {
                    "page_count": normalized_doc.page_count,
                    "processing_metadata": normalized_doc.processing_metadata,
                },
            )

            if normalized_doc.page_count > settings.max_pages:
                raise ValueError(
                    f"Document exceeds max page limit "
                    f"({normalized_doc.page_count} > {settings.max_pages})"
                )

            # --- Stage 3: Vision enrichment (images only, skipped if no GEMINI_API_KEY) ---
            job_repository.update_job_progress(job_id, 0.30, "enriching")
            logger.info(f"[PROCESSING] vision_enrich_started document_id={document_id}")
            normalized_doc = self.vision_service.enrich(normalized_doc)
            logger.info(f"[PROCESSING] vision_enrich_completed document_id={document_id}")

            # --- Stage 4: Chunk ---
            job_repository.update_job_progress(job_id, 0.45, "chunking")
            logger.info(f"[PROCESSING] chunking_started document_id={document_id}")
            chunks = self.chunker.chunk(normalized_doc)
            if not chunks:
                raise ValueError("No processable content found in document after chunking.")
            logger.info(
                f"[PROCESSING] chunking_completed document_id={document_id} chunks={len(chunks)}"
            )

            # --- Stage 5: Embed ---
            job_repository.update_job_progress(job_id, 0.60, "embedding")
            logger.info(
                f"[PROCESSING] embedding_started document_id={document_id} chunks={len(chunks)}"
            )
            chunks_with_vectors = self.embedding_service.embed(chunks)
            logger.info(
                f"[PROCESSING] embedding_completed document_id={document_id} "
                f"vectors={len(chunks_with_vectors)}"
            )

            # --- Stage 6: Index into Qdrant (first, so we can roll back if PG fails) ---
            job_repository.update_job_progress(job_id, 0.75, "indexing")
            logger.info(f"[PROCESSING] qdrant_upsert_started document_id={document_id}")
            try:
                self.qdrant_service.upsert(chunks_with_vectors, user_id)
            except Exception as e:
                logger.error(
                    f"[PROCESSING] qdrant_upsert_failed document_id={document_id} error={e}"
                )
                raise RuntimeError(f"Failed to index vectors in Qdrant: {e}") from e
            logger.info(
                f"[PROCESSING] qdrant_upsert_completed document_id={document_id} "
                f"points={len(chunks_with_vectors)}"
            )

            # --- Stage 7: Persist chunk metadata in PostgreSQL ---
            job_repository.update_job_progress(job_id, 0.90, "persisting")
            logger.info(f"[PROCESSING] pg_chunks_insert_started document_id={document_id}")
            try:
                chunk_repository.insert_chunks(chunks)
            except Exception as e:
                logger.error(
                    f"[PROCESSING] pg_chunks_insert_failed document_id={document_id} error={e}"
                )
                # Rollback Qdrant to keep stores consistent.
                try:
                    self.qdrant_service.delete_by_document(document_id, user_id)
                    logger.info(
                        f"[PROCESSING] qdrant_rollback_completed document_id={document_id}"
                    )
                except Exception as rollback_e:
                    logger.critical(
                        f"[PROCESSING] qdrant_rollback_failed document_id={document_id} "
                        f"error={rollback_e} — Qdrant and PG are now inconsistent!"
                    )
                raise RuntimeError(f"Failed to insert chunk metadata in PostgreSQL: {e}") from e
            logger.info(
                f"[PROCESSING] pg_chunks_insert_completed document_id={document_id} "
                f"chunks={len(chunks)}"
            )

            # --- Stage 8: Mark complete ---
            job_repository.complete_job(job_id)
            document_repository.update_document_status(document_id, user_id, "ready")
            logger.info(
                f"[PROCESSING] job_completed job_id={job_id} document_id={document_id} "
                f"status=ready"
            )

        except Exception as e:
            logger.error(
                f"[PROCESSING] job_failed job_id={job_id} document_id={document_id} "
                f"error={e}",
                exc_info=True,
            )
            try:
                job_repository.fail_job(
                    job_id, stage="processing", message=str(e), retry_count=0
                )
            except Exception as e_job:
                logger.error(
                    f"[PROCESSING] failed to update job status to failed: {e_job}"
                )
            try:
                document_repository.update_document_status(document_id, user_id, "failed")
            except Exception as e_doc:
                logger.error(
                    f"[PROCESSING] failed to update document status to failed: {e_doc}"
                )


async def run_orphan_recovery():
    """
    Periodic recovery task — marks any jobs/documents stuck in 'processing' or
    'queued' beyond the configured timeout as FAILED.

    Called from the main.py lifespan on a schedule. Provides a safety net for
    jobs killed by OOM/SIGKILL before their own error handlers could run.
    """
    threshold_minutes = max(1, settings.processing_timeout_seconds // 60 + 2)
    logger.info(
        f"[RECOVERY] orphan_recovery_started threshold_minutes={threshold_minutes}"
    )
    try:
        stale = job_repository.find_stale_processing_jobs(threshold_minutes)
        if not stale:
            logger.debug("[RECOVERY] no stale jobs found")
            return
        for job in stale:
            job_id = job["id"]
            document_id = job.get("document_id")
            user_id = job.get("user_id")
            logger.warning(
                f"[RECOVERY] orphan_job_detected job_id={job_id} "
                f"document_id={document_id} started_at={job.get('started_at')}"
            )
            try:
                job_repository.fail_job(
                    job_id,
                    stage="orphan_recovery",
                    message=(
                        f"Job exceeded processing timeout ({threshold_minutes} min). "
                        "Process was likely killed by OOM or SIGKILL."
                    ),
                    retry_count=0,
                )
            except Exception as e:
                logger.error(
                    f"[RECOVERY] failed to fail orphan job {job_id}: {e}"
                )
            if document_id and user_id:
                try:
                    document_repository.update_document_status(
                        document_id, user_id, "failed"
                    )
                except Exception as e:
                    logger.error(
                        f"[RECOVERY] failed to fail orphan document {document_id}: {e}"
                    )
        logger.info(f"[RECOVERY] orphan_recovery_completed recovered={len(stale)}")
    except Exception as e:
        logger.error(f"[RECOVERY] orphan_recovery_error: {e}", exc_info=True)
