"""API route modules."""

from .auth import router as auth_router
from .connections import router as connections_router
from .dashboard import router as dashboard_router
from .ingest import router as ingest_router
from .query import router as query_router
from .reports import router as reports_router
from .scheduler import router as scheduler_router

__all__ = [
    "auth_router",
    "connections_router",
    "dashboard_router",
    "ingest_router",
    "query_router",
    "reports_router",
    "scheduler_router",
]
