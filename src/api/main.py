"""FastAPI application for Marketing GraphRAG."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import get_settings
from src.graph.client import get_neo4j_client

from .routes import auth_router, dashboard_router, ingest_router, query_router, reports_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Marketing GraphRAG API...")
    settings = get_settings()

    # Initialize Neo4j connection
    neo4j = get_neo4j_client()
    if neo4j.verify_connectivity():
        logger.info("Neo4j connection established")
        neo4j.initialize_schema()
    else:
        logger.error("Failed to connect to Neo4j")

    # Initialize Azure Monitor if configured
    if settings.AZURE_MONITOR_CONNECTION_STRING:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
            logger.info("Azure Monitor telemetry enabled")
        except ImportError:
            logger.warning("Azure Monitor SDK not installed")

    yield

    # Shutdown
    logger.info("Shutting down Marketing GraphRAG API...")
    neo4j.close()


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="GraphRAG-powered marketing analytics API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(reports_router, prefix="/api")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    neo4j = get_neo4j_client()
    neo4j_healthy = neo4j.verify_connectivity()

    return {
        "status": "healthy" if neo4j_healthy else "degraded",
        "version": "0.1.0",
        "neo4j": "connected" if neo4j_healthy else "disconnected",
    }


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


# API info endpoint
@app.get("/api", tags=["Info"])
async def api_info() -> dict[str, Any]:
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "endpoints": {
            "auth": "/api/auth",
            "query": "/api/query",
            "ingest": "/api/ingest",
            "reports": "/api/reports",
        },
        "documentation": "/docs" if settings.DEBUG else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
