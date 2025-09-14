# app/main.py
"""Application entry point and FastAPI app factory."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.database import Base, engine
from app.logging_config import setup_logging, RequestLoggingMiddleware
from api import sensors as sensors_router
from api import metrics as metrics_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    
    # Configure structured logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)
    logger.info("Starting Climate Stats API", extra={"log_level": log_level})

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Development convenience: auto-create tables at startup.
        # In production, replace with Alembic migrations.
        logger.info("Initializing database tables")
        Base.metadata.create_all(bind=engine)
        logger.info("Application startup complete")
        yield
        logger.info("Application shutdown")
        # Optional teardown logic can be added here if needed.

    app = FastAPI(
        title="Climate Stats API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # CORS middleware: permissive for demo purposes; restrict in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root route - meta endpoint
    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"message": "Climate Stats API"}

    # Healthcheck endpoint (used by tests and orchestration systems)
    @app.get("/healthz", tags=["health"])
    def healthz() -> dict:
        return {"status": "ok"}

    # Register routers (each API module exposes a `router` object)
    app.include_router(sensors_router.router)
    app.include_router(metrics_router.router)

    return app