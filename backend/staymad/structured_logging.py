"""Structured JSON Logging for Stay Mad.

Authority: docs/architecture/J-cloud-run-architecture.md (§7.2), docs/decisions.md (DEC-0006)
Compatible directly with Google Cloud Logging on Google Cloud Run.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

# Map Python log levels to Google Cloud Logging Severity levels
SEVERITY_MAP: dict[int, str] = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class CloudLoggingFormatter(logging.Formatter):
    """Google Cloud Logging compatible JSON log formatter.

    Outputs single-line JSON log events parsing keys:
    - severity: Google Cloud Logging standard severity level
    - message: Log message text
    - time: RFC3339 / ISO8601 UTC timestamp
    - logger: Logger name
    - stage, processing_run_id, latency_ms, duration_ms: Custom pipeline metadata
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        severity = SEVERITY_MAP.get(record.levelno, "DEFAULT")

        log_payload: dict[str, Any] = {
            "severity": severity,
            "message": record.getMessage(),
            "time": timestamp,
            "logger": record.name,
        }

        # Include standard context fields if provided in extra
        for field in (
            "processing_run_id",
            "stage",
            "latency_ms",
            "duration_ms",
            "article_version_id",
            "claim_count",
            "model_version",
            "path",
            "method",
            "status_code",
            "client_ip",
        ):
            val = getattr(record, field, None)
            if val is not None:
                log_payload[field] = (
                    str(val) if not isinstance(val, (int, float, bool)) else val
                )

        # Handle exception information if present
        if record.exc_info:
            log_payload["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)


def setup_structured_logging(
    log_level: str | None = None,
    json_format: bool | None = None,
) -> None:
    """Configure system-wide logging with Cloud Logging support."""
    env = os.getenv("STAYMAD_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    default_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level_name = log_level.upper() if log_level else default_log_level
    numeric_level = getattr(logging, level_name, logging.INFO)

    if json_format is None:
        log_format_env = os.getenv("LOG_FORMAT", "").lower()
        json_format = (env == "production") or (log_format_env == "json")

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if json_format:
        console_handler.setFormatter(CloudLoggingFormatter())
    else:
        standard_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
        console_handler.setFormatter(logging.Formatter(standard_format))

    root_logger.addHandler(console_handler)

    # Configure uvicorn access & error loggers
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        u_logger = logging.getLogger(uvicorn_logger_name)
        u_logger.setLevel(numeric_level)
