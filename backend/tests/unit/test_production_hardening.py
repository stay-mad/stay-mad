"""Unit tests for Production Hardening & Structured Cloud Logging.

Authority: docs/decisions.md (DEC-0006), docs/architecture/J-cloud-run-architecture.md (§7.2)
"""

import json
import logging
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.staymad.api.main import app, perform_startup_checks
from backend.staymad.structured_logging import CloudLoggingFormatter


def test_cloud_logging_formatter_structure():
    """Verify JSON output structure matches Google Cloud Logging expectations."""
    formatter = CloudLoggingFormatter()
    record = logging.LogRecord(
        name="staymad.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Claim extraction pipeline completed",
        args=(),
        exc_info=None,
    )
    record.processing_run_id = "test-run-1234"
    record.stage = "claim_extracted"
    record.latency_ms = 42.5
    record.claim_count = 8

    formatted_str = formatter.format(record)
    parsed = json.loads(formatted_str)

    assert parsed["severity"] == "INFO"
    assert parsed["message"] == "Claim extraction pipeline completed"
    assert parsed["logger"] == "staymad.test"
    assert "time" in parsed
    assert parsed["processing_run_id"] == "test-run-1234"
    assert parsed["stage"] == "claim_extracted"
    assert parsed["latency_ms"] == 42.5
    assert parsed["claim_count"] == 8


def test_production_startup_guard_blocks_fixture_mode():
    """DEC-0006: Boot must fail if fixture_mode is True in production."""
    with (
        patch.dict(os.environ, {"ENVIRONMENT": "production", "FIXTURE_MODE": "true"}),
        pytest.raises(
            RuntimeError, match="FATAL: Fixture / mock adapter cannot be used"
        ),
    ):
        perform_startup_checks()


def test_production_startup_guard_blocks_missing_gemini_key():
    """DEC-0006: Boot must fail if GEMINI_API_KEY is missing in production."""
    with (
        patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "FIXTURE_MODE": "false",
                "GEMINI_API_KEY": "",
            },
        ),
        pytest.raises(RuntimeError, match="FATAL: GEMINI_API_KEY is required"),
    ):
        perform_startup_checks()


def test_health_endpoint_production_invariants():
    """DEC-0006: /health returns HTTP 503 if misconfigured in production."""
    client = TestClient(app)
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "production", "FIXTURE_MODE": "true", "GEMINI_API_KEY": ""},
    ):
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "error"
        assert "FATAL" in data["details"]
