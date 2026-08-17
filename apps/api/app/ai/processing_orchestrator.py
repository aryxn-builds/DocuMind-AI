"""
DocuMind AI — Processing Orchestrator.

Runs the full document ingestion pipeline:
  download → parse → vision-enrich → chunk → embed → upsert-qdrant → pg-chunks → mark-ready

Architecture on Render Free Tier
---------------------------------
We use FastAPI BackgroundTasks with a SYNC background task function
(`run_as_background_task`). Starlette runs sync background tasks via
`anyio.to_thread.run_sync`, which is a simple thread-pool dispatch —
no asyncio primitives, no event-loop dependencies, no `asyncio.to_thread`.

This is intentional. Previous versions used an `async def run()` wrapper that
called `asyncio.to_thread` inside, which caused silent failures on Render when
the process lifecycle ended before the coroutine was awaited.

Concurrency is controlled by a `threading.Semaphore` (not asyncio.Semaphore)
because the background task runs in a thread, not in an async context.

Every stage emits a structured [PROCESSING] log line so Render logs can be
grep'd to find exactly where execution stopped.

The orphan recovery loop (`run_orphan_recovery`) runs every 5 minutes from
`main.py` and marks any jobs/documents still stuck in processing/queued
beyond the timeout as FAILED, providing a safety net for process kills.
"""

import logging
import threading

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

# Thread-safe semaphore for limiting concurrent background jobs.
# Uses threading.Semaphore (not asyncio.Semaphore) because the background
# task runs in a thread pool, not in an async event loop.
_thread_semaphore = threading.Semaphore(settings.concurrent_processing_limit)


class ProcessingOrchestrator:
    def __init__(self):
        self.vision_service = VisionEnrichmentService()
        self.chunker = Chunker()
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()

    def run_as_background_task(
        self, job_id: str, document_id: str, user_id: str
    ) -> None:
        """
        Sync entry point for FastAPI BackgroundTasks.

        Starlette runs sync background tasks via anyio.to_thread.run_sync —
        a clean thread-pool dispatch with no asyncio dependencies.

        A threading.Semaphore limits concurrency. If the semaphore cannot be
        acquired within 30 seconds, the job is marked FAILED immediately rather
        than queuing indefinitely.
        """
        logger.info(
            f"[PROCESSING] task_created job_id={job_id} document_id={document_id}"
        )

        acquired = _thread_semaphore.acquire(timeout=30)
        if not acquired:
            logger.error(
                f"[PROCESSING] semaphore_timeout job_id={job_id} — "
                f"too many concurrent jobs, marking failed."
            )
            try:
                job_repository.fail_job(
                    job_id,
                    stage="semaphore",
                    message="Could not acquire processing semaphore within 30 seconds.",
                    retry_count=0,
                )
                document_repository.update_document_status(document_id, user_id, "failed")
            except Exception as e:
                logger.error(f"[PROCESSING] failed to mark semaphore-timeout job: {e}")
            return

        logger.info(
            f"[PROCESSING] task_started job_id={job_id} document_id={document_id}"
        )
        try:
            self._run_sync(job_id, document_id, user_id)
        except Exception as e:
            # Safety net — _run_sync has its own try/except but this ensures
            # the semaphore is always released even on unexpected exceptions.
            logger.error(
                f"[PROCESSING] task_failed job_id={job_id} document_id={document_id} "
                f"unhandled_error={e}",
                exc_info=True,
            )
        finally:
            _thread_semaphore.release()
            logger.info(
                f"[PROCESSING] task_finished job_id={job_id} document_id={document_id}"
            )

    @observe(as_type="generation", name="Process Document")
    def _run_sync(self, job_id: str, document_id: str, user_id: str) -> None:
        """
        Synchronous processing pipeline. Runs in a thread pool via Starlette's
        anyio.to_thread.run_sync (dispatched from run_as_background_task).

        Guarantees: every code path ends with job status = completed | failed.
        The document status is set to processing → ready | failed.
        """

        # --- Claim the job atomically (prevents double-processing on retry) ---
        job = job_repository.claim_job(job_id)
        if not job:
            logger.info(
                f"[PROCESSING] job_already_claimed job_id={job_id} — skipping."
            )
            return

        logger.info(
            f"[PROCESSING] job_started job_id={job_id} document_id={document_id}"
        )
        try:
            document_repository.update_document_status(document_id, user_id, "processing")
        except Exception as e:
            logger.error(
                f"[PROCESSING] failed to set document to processing: {e}", exc_info=True
            )

        try:
            # Idempotent cleanup: remove any vectors/chunks from a prior failed attempt.
            logger.info(f"[PROCESSING] cleanup_started document_id={document_id}")
            try:
                self.qdrant_service.delete_by_document(document_id, user_id)
                chunk_repository.delete_by_document(document_id, user_id)
            except Exception as e:
                # Non-fatal — log and continue; the upsert below is idempotent.
                logger.warning(
                    f"[PROCESSING] cleanup_partial document_id={document_id} error={e}"
                )
            logger.info(f"[PROCESSING] cleanup_completed document_id={document_id}")

            doc = document_repository.get_document_by_id(document_id, user_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found in database.")

            file_path = doc["file_path"]
            mime_type = doc["file_type"]
            title = doc["title"]

            # ------------------------------------------------------------------
            # Stage 1: Download
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.05, "downloading")
            logger.info(
                f"[PROCESSING] download_started document_id={document_id} path={file_path}"
            )
            file_bytes = storage_service.download_document(file_path)
            if not file_bytes:
                raise RuntimeError(
                    f"Empty or missing file at path '{file_path}'. "
                    "Storage upload may not have completed."
                )
            logger.info(
                f"[PROCESSING] download_completed document_id={document_id} "
                f"size_bytes={len(file_bytes)}"
            )

            # ------------------------------------------------------------------
            # Stage 2: Parse
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.15, "parsing")
            logger.info(
                f"[PROCESSING] parse_started document_id={document_id} "
                f"mime_type={mime_type}"
            )
            adapter = get_adapter(document_id, user_id, file_path, mime_type, title)
            normalized_doc = adapter.parse(file_bytes)
            logger.info(
                f"[PROCESSING] parse_completed document_id={document_id} "
                f"pages={normalized_doc.page_count} blocks={len(normalized_doc.blocks)}"
            )

            try:
                document_repository.update_document_metadata(
                    document_id,
                    user_id,
                    {
                        "page_count": normalized_doc.page_count,
                        "processing_metadata": normalized_doc.processing_metadata,
                    },
                )
            except Exception as e:
                logger.warning(
                    f"[PROCESSING] metadata_update_failed document_id={document_id} "
                    f"error={e} (non-fatal)"
                )

            if normalized_doc.page_count > settings.max_pages:
                raise ValueError(
                    f"Document exceeds max page limit "
                    f"({normalized_doc.page_count} > {settings.max_pages})"
                )

            # ------------------------------------------------------------------
            # Stage 3: Vision enrichment (images only)
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.30, "enriching")
            logger.info(
                f"[PROCESSING] vision_enrich_started document_id={document_id}"
            )
            try:
                normalized_doc = self.vision_service.enrich(normalized_doc)
            except Exception as e:
                # Non-fatal — vision enrichment is best-effort for PDFs.
                logger.warning(
                    f"[PROCESSING] vision_enrich_failed document_id={document_id} "
                    f"error={e} (continuing without enrichment)"
                )
            logger.info(
                f"[PROCESSING] vision_enrich_completed document_id={document_id}"
            )

            # ------------------------------------------------------------------
            # Stage 4: Chunk
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.45, "chunking")
            logger.info(f"[PROCESSING] chunking_started document_id={document_id}")
            chunks = self.chunker.chunk(normalized_doc)
            if not chunks:
                raise ValueError(
                    "No processable content extracted from document. "
                    "The file may be empty, image-only, or corrupted."
                )
            logger.info(
                f"[PROCESSING] chunking_completed document_id={document_id} "
                f"chunks={len(chunks)}"
            )

            # ------------------------------------------------------------------
            # Stage 5: Embed
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.60, "embedding")
            logger.info(
                f"[PROCESSING] embedding_started document_id={document_id} "
                f"chunks={len(chunks)}"
            )
            chunks_with_vectors = self.embedding_service.embed(chunks)
            logger.info(
                f"[PROCESSING] embedding_completed document_id={document_id} "
                f"vectors={len(chunks_with_vectors)}"
            )

            # ------------------------------------------------------------------
            # Stage 6: Upsert into Qdrant
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.75, "indexing")
            logger.info(
                f"[PROCESSING] qdrant_upsert_started document_id={document_id}"
            )
            try:
                self.qdrant_service.upsert(chunks_with_vectors, user_id)
            except Exception as e:
                logger.error(
                    f"[PROCESSING] qdrant_upsert_failed document_id={document_id} "
                    f"error={e}",
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Qdrant upsert failed: {e}. "
                    "Check QDRANT_URL and QDRANT_API_KEY in Render env vars, "
                    "and verify collection dimension = 768."
                ) from e
            logger.info(
                f"[PROCESSING] qdrant_upsert_completed document_id={document_id} "
                f"points={len(chunks_with_vectors)}"
            )

            # ------------------------------------------------------------------
            # Stage 7: Persist chunk metadata in PostgreSQL
            # ------------------------------------------------------------------
            job_repository.update_job_progress(job_id, 0.90, "persisting")
            logger.info(
                f"[PROCESSING] pg_chunks_insert_started document_id={document_id}"
            )
            try:
                chunk_repository.insert_chunks(chunks)
            except Exception as e:
                logger.error(
                    f"[PROCESSING] pg_chunks_insert_failed document_id={document_id} "
                    f"error={e}",
                    exc_info=True,
                )
                # Rollback Qdrant to keep stores consistent.
                try:
                    self.qdrant_service.delete_by_document(document_id, user_id)
                    logger.info(
                        f"[PROCESSING] qdrant_rollback_completed "
                        f"document_id={document_id}"
                    )
                except Exception as rollback_e:
                    logger.critical(
                        f"[PROCESSING] qdrant_rollback_failed "
                        f"document_id={document_id} error={rollback_e} "
                        "— Qdrant and PG are now inconsistent!"
                    )
                raise RuntimeError(
                    f"PostgreSQL chunk insert failed: {e}"
                ) from e
            logger.info(
                f"[PROCESSING] pg_chunks_insert_completed document_id={document_id} "
                f"chunks={len(chunks)}"
            )

            # ------------------------------------------------------------------
            # Stage 8: Mark complete
            # ------------------------------------------------------------------
            job_repository.complete_job(job_id)
            document_repository.update_document_status(document_id, user_id, "ready")
            logger.info(
                f"[PROCESSING] job_completed job_id={job_id} "
                f"document_id={document_id} status=ready"
            )

        except Exception as e:
            logger.error(
                f"[PROCESSING] job_failed job_id={job_id} "
                f"document_id={document_id} error={e}",
                exc_info=True,
            )
            try:
                job_repository.fail_job(
                    job_id, stage="processing", message=str(e), retry_count=0
                )
            except Exception as e_job:
                logger.error(
                    f"[PROCESSING] could not mark job failed: {e_job}"
                )
            try:
                document_repository.update_document_status(
                    document_id, user_id, "failed"
                )
            except Exception as e_doc:
                logger.error(
                    f"[PROCESSING] could not mark document failed: {e_doc}"
                )


async def run_orphan_recovery() -> None:
    """
    Periodic recovery task — marks any jobs/documents stuck in 'processing' or
    'queued' beyond the configured timeout as FAILED.

    Called from the main.py lifespan on a 5-minute schedule.
    Provides a safety net for jobs killed by Render SIGTERM/SIGKILL before
    their own error handlers could run.
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
                        f"Job exceeded timeout ({threshold_minutes} min). "
                        "Process was likely killed by Render SIGTERM/SIGKILL."
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
                        f"[RECOVERY] failed to fail orphan document "
                        f"{document_id}: {e}"
                    )
        logger.info(
            f"[RECOVERY] orphan_recovery_completed recovered={len(stale)}"
        )
    except Exception as e:
        logger.error(f"[RECOVERY] orphan_recovery_error: {e}", exc_info=True)
