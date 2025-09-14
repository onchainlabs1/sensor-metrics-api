# app/database.py
"""Database engine, session factory, and dependency for DB access."""

from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to local SQLite; can be swapped for Postgres via env var.
# Example for Postgres:
# DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./weather.db")

# SQLite needs check_same_thread=False for file-based DB in single process
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()