"""
DocuMind AI — FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
from contextlib import asynccontextmanager

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.repositories import job_repository

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: fail any jobs that were left running or queued when the process crashed
    try:
        count = job_repository.fail_stale_jobs("Process restarted unexpectedly")
        if count > 0:
            logger.warning(f"Marked {count} stale jobs as failed during startup.")
    except Exception as e:
        logger.error(f"Failed to run stale job sweep: {e}")
        
    yield
    # Shutdown

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
