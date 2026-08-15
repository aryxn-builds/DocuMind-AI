"""
DocuMind AI — FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multimodal document intelligence API.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
