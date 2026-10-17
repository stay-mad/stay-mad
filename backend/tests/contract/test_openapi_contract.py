"""Contract synchronization tests for docs/contracts/openapi.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = REPO_ROOT / "docs" / "contracts" / "openapi.yaml"


def test_openapi_file_exists_and_parses():
    assert OPENAPI_PATH.exists(), f"OpenAPI contract must exist at {OPENAPI_PATH}"
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    assert spec.get("openapi") == "3.1.0"
    assert "paths" in spec
    assert "components" in spec
    assert "schemas" in spec["components"]


def test_openapi_required_endpoints_present():
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    paths = spec["paths"]
    expected_paths = [
        "/events",
        "/events/{id}",
        "/events/{id}/timeline",
        "/events/{id}/sources",
        "/events/{id}/changes",
        "/events/{id}/analysis",
        "/events/{id}/processing",
        "/locations",
        "/health",
    ]
    for p in expected_paths:
        assert p in paths, f"Path {p} must be declared in OpenAPI spec"


def test_openapi_category_3_enums_and_fields():
    """Verify Category 3 fixes (F-1 to F-7) from docs/reviews/review-report.md."""
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    schemas = spec["components"]["schemas"]

    # F-1: ClaimStatus enum
    assert "ClaimStatus" in schemas
    assert schemas["ClaimStatus"]["enum"] == [
        "CONFIRMED",
        "SUPPORTED",
        "UNCONFIRMED",
        "CONFLICTING",
        "UNKNOWN",
    ]

    # F-2: ResolutionDecision enum
    assert "ResolutionDecision" in schemas
    assert schemas["ResolutionDecision"]["enum"] == [
        "SAME_EVENT",
        "RELATED_EVENT",
        "SEPARATE_EVENT",
        "NEEDS_REVIEW",
    ]

    # F-3: SourceTier enum promoted to named component
    assert "SourceTier" in schemas
    assert schemas["SourceTier"]["enum"] == ["TIER_1", "TIER_2"]
    source_item = schemas["SourceItem"]["properties"]
    assert source_item["source_tier"]["$ref"] == "#/components/schemas/SourceTier"

    # F-4: ChangeCategory enum and optional change_category on ChangeItem
    assert "ChangeCategory" in schemas
    assert schemas["ChangeCategory"]["enum"] == [
        "AREA_CHANGE",
        "ALERT_STATUS",
        "ESCALATION",
        "NUMERICAL",
        "NEWLY_CONFIRMED",
        "NEWLY_CONFLICTING",
    ]
    change_item = schemas["ChangeItem"]["properties"]
    assert (
        change_item["change_category"]["$ref"] == "#/components/schemas/ChangeCategory"
    )
    assert change_item["change_category"].get("nullable") is True

    # F-5: correlation_id on ProcessingResponse
    proc_props = schemas["ProcessingResponse"]["properties"]
    assert "correlation_id" in proc_props
    assert proc_props["correlation_id"]["type"] == "string"
    assert proc_props["correlation_id"].get("nullable") is True

    # F-6: DataMode supports degraded
    assert "DataMode" in schemas
    assert set(schemas["DataMode"]["enum"]) == {"live", "demo", "degraded"}

    # F-7: Canonical temporal qualifiers documented
    assert "TimelineQualifier" in schemas
    assert set(schemas["TimelineQualifier"]["enum"]) == {
        "sekitar",
        "sebelum",
        "diperkirakan",
        "dilaporkan_pada",
        "tepat",
    }
    timeline_entry = schemas["TimelineEntry"]["properties"]
    assert (
        timeline_entry["event_time_qualifier"]["$ref"]
        == "#/components/schemas/TimelineQualifier"
    )
    assert timeline_entry["event_time_qualifier"].get("nullable") is True
