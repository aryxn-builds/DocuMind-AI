"""
DocuMind AI — API v1 Router.

All product endpoints will be registered here during feature implementation phases.
This file acts as the top-level aggregator for v1 sub-routers.
"""

from fastapi import APIRouter

api_v1_router = APIRouter()


# ---------------------------------------------------------------------------
# Placeholder — confirms the /api/v1 prefix is wired correctly.
# Remove once the first real endpoint group is registered.
# ---------------------------------------------------------------------------
@api_v1_router.get("/ping", tags=["health"], summary="API v1 ping")
async def ping() -> dict[str, str]:
    """Confirms the /api/v1 prefix is reachable."""
    return {"ping": "pong"}


# ---------------------------------------------------------------------------
# Future endpoint routers are registered below (uncomment as implemented):
# ---------------------------------------------------------------------------
# from app.api.v1.endpoints import auth, documents, conversations, search, collections
# api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
# api_v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])  # noqa: E501
# api_v1_router.include_router(search.router, prefix="/search", tags=["search"])
# api_v1_router.include_router(collections.router, prefix="/collections", tags=["collections"])
