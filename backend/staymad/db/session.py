"""Database engine and session management.

Authority: docs/architecture/B-data-model.md §1
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DB_URL = "sqlite:///:memory:"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def create_db_engine(db_url: str | None = None) -> Engine:
    url = db_url or get_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    eng = engine or create_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    factory = create_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
