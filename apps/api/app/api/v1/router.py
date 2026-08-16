"""
DocuMind AI — API v1 Router.

All product endpoints will be registered here during feature implementation phases.
This file acts as the top-level aggregator for v1 sub-routers.
"""

from fastapi import APIRouter

api_v1_router = APIRouter()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
from app.api.v1.endpoints import auth, chat, documents

# from app.api.v1.endpoints import collections
api_v1_router.include_router(auth.router, prefix="", tags=["auth"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(chat.router, prefix="", tags=["chat"])
# api_v1_router.include_router(collections.router, prefix="/collections", tags=["collections"])
