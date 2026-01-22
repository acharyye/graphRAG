"""API route modules."""

from .auth import router as auth_router
from .ingest import router as ingest_router
from .query import router as query_router
from .reports import router as reports_router

__all__ = ["auth_router", "query_router", "ingest_router", "reports_router"]
