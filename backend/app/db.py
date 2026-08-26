"""Database wiring. SQLite by default; a real PostgreSQL instance is used
when `TRACKER_DATABASE_URL` is set. PostgreSQL is not installed as a
service on the build machine, so PostgreSQL-backed tests skip cleanly when
it is unreachable (see `tests/test_postgres_store.py`).
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


def make_engine(database_url: str | None = None):
    url = database_url or os.environ.get("TRACKER_DATABASE_URL", "sqlite:///:memory:")
    if url == "sqlite:///:memory:":
        # An in-memory SQLite database is private to the connection that
        # created it; the default pool hands out a fresh connection (and so
        # a fresh, empty database) per checkout. StaticPool keeps a single
        # connection alive for the engine's lifetime so every session
        # (every FastAPI request, every test) sees the same database.
        engine = create_engine(url, future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine


def make_session(engine) -> Session:
    return sessionmaker(bind=engine, future=True)()
