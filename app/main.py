# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

# Routers (note: `api` is a top-level package, sibling of `app`)
from api import sensors as sensors_router
from api import metrics as metrics_router


def create_app() -> FastAPI:
    """
    Application factory.
    Creates FastAPI instance, mounts routers and middlewares.
    """
    app = FastAPI(
        title="Climate Stats API",
        version="0.1.0",
        description="Weather metrics ingestion and query service"
    )

    # Basic CORS for local development / tests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tables on startup (SQLite dev only; for production use migrations)
    @app.on_event("startup")
    def _create_tables() -> None:
        Base.metadata.create_all(bind=engine)

    # Mount routers
    app.include_router(sensors_router.router)
    app.include_router(metrics_router.router)

    @app.get("/healthz", tags=["health"])
    def healthcheck():
        return {"status": "ok"}

    return app