"""Main FastAPI application entrypoint for Stay Mad.

Authority: docs/contracts/openapi.yaml, docs/decisions.md (DEC-0006), docs/architecture/J-cloud-run-architecture.md
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from backend.staymad.api.middleware import (
    setup_cors,
    setup_exception_handlers,
    setup_logging_middleware,
)
from backend.staymad.api.routers import events, jobs, locations, system
from backend.staymad.structured_logging import setup_structured_logging

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_CONTRACT_PATH = REPO_ROOT / "docs" / "contracts" / "openapi.yaml"

logger = logging.getLogger("staymad.api")


def perform_startup_checks() -> None:
    """Validate critical startup configuration per DEC-0006.

    In production environment:
    - Boot must fail if fixture / mock adapter is active.
    - Boot must fail if GEMINI_API_KEY is missing or invalid.
    """
    env = os.getenv("STAYMAD_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    fixture_mode = os.getenv("FIXTURE_MODE", "false").lower() in (
        "true",
        "1",
    ) or os.getenv("USE_MOCK_GEMINI", "false").lower() in ("true", "1")
    if env == "production":
        if fixture_mode:
            raise RuntimeError(
                "FATAL: Fixture / mock adapter cannot be used in production environment (DEC-0006)."
            )
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            raise RuntimeError(
                "FATAL: GEMINI_API_KEY is required in production environment (DEC-0006)."
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context enforcing startup checks and graceful shutdown handling."""
    # 1. Initialize structured logging
    setup_structured_logging()
    # 2. Run invariants checks
    perform_startup_checks()
    logger.info(
        "Stay Mad API server initialized successfully.",
        extra={
            "stage": "startup",
            "environment": os.getenv("ENVIRONMENT", "development"),
        },
    )
    yield
    # 3. Graceful shutdown cleanup (SIGTERM from Cloud Run scaling)
    logger.info(
        "Stay Mad API server shutting down gracefully (SIGTERM/SIGINT received).",
        extra={"stage": "shutdown"},
    )


def create_app() -> FastAPI:
    """Application factory for Stay Mad FastAPI backend."""
    app = FastAPI(
        title="Stay Mad API",
        version="0.1.0",
        description="REST API untuk platform Event Intelligence Stay Mad.",
        lifespan=lifespan,
    )

    # 1. Setup CORS, structured request logging & error handling
    setup_cors(app)
    setup_logging_middleware(app)
    setup_exception_handlers(app)

    # 2. Register routers
    app.include_router(events.router)
    app.include_router(locations.router)
    app.include_router(system.router)
    app.include_router(jobs.router)

    # 3. Mount custom OpenAPI contract schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        if OPENAPI_CONTRACT_PATH.exists():
            with open(OPENAPI_CONTRACT_PATH, "r", encoding="utf-8") as f:
                contract_spec = yaml.safe_load(f)
            app.openapi_schema = contract_spec
            return app.openapi_schema
        return app.openapi()

    app.openapi = custom_openapi

    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/docs")

    return app


app = create_app()


def run_dev_server() -> None:
    """CLI runner to launch server."""
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "127.0.0.1")
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")
    print(f"==> Starting Stay Mad API Server on http://{host}:{port} (reload={reload})")
    uvicorn.run("backend.staymad.api.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_dev_server()
