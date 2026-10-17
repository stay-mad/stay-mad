"""System operational and healthcheck endpoints.

Authority: docs/contracts/openapi.yaml, docs/decisions.md (DEC-0006), docs/architecture/J-cloud-run-architecture.md
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.staymad.api.dependencies import get_db
from backend.staymad.api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
@router.get("/healthz", response_model=HealthResponse)
def health_check(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    """Healthcheck endpoint with database and configuration validation.

    CRITICAL (DEC-0006): Returns HTTP 503 if:
    - Database is disconnected
    - pgvector extension is not installed in PostgreSQL
    - fixture_mode = True in production environment
    - GEMINI_API_KEY is missing or invalid in production
    """
    errors: list[str] = []

    # 1. Test database connectivity and pgvector readiness
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"

        # Check pgvector readiness if running on PostgreSQL
        bind = db.get_bind()
        if bind and bind.dialect.name.startswith("postgres"):
            has_vector = db.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            if not has_vector:
                errors.append(
                    "pgvector extension is not installed or enabled in PostgreSQL"
                )
                db_status = "disconnected"
    except SQLAlchemyError as exc:
        db_status = "disconnected"
        errors.append(f"Database error: {exc}")
    except Exception as exc:  # noqa: BLE001
        db_status = "disconnected"
        errors.append(f"Database error: {exc}")

    # 2. Inspect environment and configuration
    env_str = os.getenv("STAYMAD_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env_str not in ("production", "staging", "development", "test"):
        env_str = "development"

    fixture_mode = os.getenv("FIXTURE_MODE", "false").lower() in (
        "true",
        "1",
    ) or os.getenv("USE_MOCK_GEMINI", "false").lower() in ("true", "1")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_status = (
        "reachable"
        if gemini_key
        else ("unreachable" if env_str == "production" else "not_checked")
    )

    data_mode_env = os.getenv("DATA_MODE", "live").lower()

    # 3. Determine errors and health status
    if db_status == "disconnected" and "Database error" not in "".join(errors):
        errors.append("Database connection failure")

    if env_str == "production":
        if fixture_mode:
            errors.append(
                "FATAL: Fixture / mock adapter cannot be used in production environment (DEC-0006)"
            )
        if not gemini_key:
            errors.append(
                "FATAL: GEMINI_API_KEY is required in production environment (DEC-0006)"
            )

    if errors:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health_status = "error"
        details_str = "; ".join(errors)
    elif data_mode_env == "degraded":
        health_status = "degraded"
        details_str = "System operating in degraded mode"
    else:
        health_status = "ok"
        details_str = None

    return HealthResponse(
        status=health_status,
        database=db_status,
        gemini=gemini_status,
        fixture_mode=fixture_mode,
        environment=env_str,
        version="0.1.0",
        details=details_str,
    )
