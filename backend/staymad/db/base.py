"""Database base declarative configuration and types."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# Dual-dialect JSON type: JSONB on PostgreSQL, JSON on SQLite/others
JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Base class for all Stay Mad SQLAlchemy models."""
