"""FastAPI dependency injection utilities.

Authority: docs/architecture/A-product-architecture.md
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.staymad.db.session import get_db_session


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session for request lifecycle."""
    yield from get_db_session()
