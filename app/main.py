# app/main.py
"""Application entry point and FastAPI app factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from api import sensors as sensors_router
from api import metrics as metrics_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Development convenience: auto-create tables at startup.
        # In production, replace with Alembic migrations.
        Base.metadata.create_all(bind=engine)
        yield
        # Optional teardown logic can be added here if needed.

    app = FastAPI(
        title="Climate Stats API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

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