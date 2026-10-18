"""CORS, structured logging, and error handling middleware for Stay Mad API.

Authority: docs/contracts/openapi.yaml, docs/architecture/A-product-architecture.md, docs/architecture/J-cloud-run-architecture.md
"""

from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("staymad.api.access")


def setup_cors(app: FastAPI) -> None:
    """Configure CORS for local frontend (port 3000) and configurable origins."""
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"^https://.*\.run\.app$|^http://localhost(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_logging_middleware(app: FastAPI) -> None:
    """Structured request logging middleware compatible with Google Cloud Logging."""

    @app.middleware("http")
    async def cloud_logging_middleware(request: Request, call_next):
        start_time = time.perf_counter()
        processing_run_id = (
            request.headers.get("X-Processing-Run-Id")
            or request.query_params.get("processing_run_id")
            or None
        )

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                f"Unhandled error in HTTP {request.method} {request.url.path}",
                extra={
                    "stage": "api_request",
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": 500,
                    "latency_ms": duration_ms,
                    "duration_ms": duration_ms,
                    "processing_run_id": processing_run_id,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Processing-Time-Ms"] = str(duration_ms)

        log_level = (
            logging.ERROR
            if status_code >= 500
            else (logging.WARNING if status_code >= 400 else logging.INFO)
        )
        msg = f"{request.method} {request.url.path} -> {status_code} ({duration_ms}ms)"

        logger.log(
            log_level,
            msg,
            extra={
                "stage": "api_request",
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "latency_ms": duration_ms,
                "duration_ms": duration_ms,
                "processing_run_id": processing_run_id,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        return response


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup standardized error handlers adhering to ErrorResponse contract."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        error_type = "http_error"
        if exc.status_code == 404:
            error_type = "not_found"
        elif exc.status_code == 400:
            error_type = "bad_request"
        elif exc.status_code == 403:
            error_type = "forbidden"
        elif exc.status_code == 503:
            error_type = "service_unavailable"

        if isinstance(exc.detail, dict):
            error_code = exc.detail.get("error", error_type)
            message = exc.detail.get("message", "Terjadi kesalahan")
            details = exc.detail.get("details", None)
        else:
            error_code = error_type
            message = str(exc.detail) if exc.detail else "Terjadi kesalahan"
            details = None

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error_code,
                "message": message,
                "details": details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Parameter tidak valid atau skema tidak terpenuhi",
                "details": {"validation_errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        env = os.getenv("STAYMAD_ENV", os.getenv("ENVIRONMENT", "development")).lower()
        detail_msg = str(exc) if env != "production" else None
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Terjadi kesalahan internal pada server",
                "details": {"error": detail_msg} if detail_msg else None,
            },
        )
