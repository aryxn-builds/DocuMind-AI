"""
DocuMind AI — FastAPI Application Entry Point.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.processing_orchestrator import run_orphan_recovery
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.repositories import job_repository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Orphan recovery loop
# ---------------------------------------------------------------------------

async def _orphan_recovery_loop():
    """
    Runs indefinitely, calling run_orphan_recovery every RECOVERY_INTERVAL_SECONDS.

    This ensures that any job silently killed by OOM or SIGKILL (which bypasses
    Python's try/except) gets marked FAILED within a bounded time window, so users
    always see a terminal state (ready or failed) and never see infinite PROCESSING.
    """
    RECOVERY_INTERVAL_SECONDS = 300  # every 5 minutes
    while True:
        await asyncio.sleep(RECOVERY_INTERVAL_SECONDS)
        await run_orphan_recovery()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # 1. Clean up any jobs that were in-flight when the process last crashed.
    try:
        count = job_repository.fail_stale_jobs("Process restarted — job was orphaned.")
        if count > 0:
            logger.warning(
                f"[STARTUP] Marked {count} stale job(s) as failed during startup."
            )
        else:
            logger.info("[STARTUP] No stale jobs found.")
    except Exception as e:
        logger.error(f"[STARTUP] Failed to run stale job sweep: {e}")

    # 2. Start the periodic orphan recovery background loop.
    recovery_task = asyncio.create_task(_orphan_recovery_loop())
    logger.info("[STARTUP] Orphan recovery loop started.")

    # 3. Model availability diagnostics
    if settings.groq_api_key:
        try:
            import groq
            from app.ai.gateway import gateway
            client = groq.AsyncGroq(api_key=settings.groq_api_key)
            models = await client.models.list()
            available_models = [m.id for m in models.data]
            logger.info(f"[STARTUP] Groq configured model: {settings.groq_model}")
            if settings.groq_model not in available_models:
                logger.warning(
                    f"[STARTUP] Configured Groq model '{settings.groq_model}' is not available "
                    f"for this API key. Available models: {available_models}. "
                    "Disabling Groq to prevent 404 errors; defaulting to Gemini fallback."
                )
                gateway.groq_api_key = None
            else:
                logger.info(f"[STARTUP] Groq model '{settings.groq_model}' is available.")
        except Exception as e:
            logger.error(f"[STARTUP] Failed to verify Groq model availability: {e}")

    yield

    # --- Shutdown ---
    recovery_task.cancel()
    try:
        await recovery_task
    except asyncio.CancelledError:
        pass
    logger.info("[SHUTDOWN] Orphan recovery loop stopped.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multimodal document intelligence API.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_v1_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health endpoints (root level — not versioned, for infrastructure probes)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    """
    Liveness check.

    Returns 200 if the application process is running.
    Does NOT check external dependencies — use /ready for that.
    """
    return {"status": "ok", "version": settings.app_version}


@app.get("/ready", tags=["health"], summary="Readiness probe")
async def ready() -> dict[str, str]:
    """
    Readiness check.

    Returns 200 when the application is ready to serve requests.
    Detailed infrastructure checks (database, Qdrant) will be added
    during the infrastructure implementation phase.
    """
    return {"status": "ready", "version": settings.app_version}
