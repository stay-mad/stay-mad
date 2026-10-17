"""Tests for Gold Evaluation Set integrity and path isolation (ADR-008)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = REPO_ROOT / "eval"
GOLD_DIR = EVAL_DIR / "gold"
BACKEND_DIR = REPO_ROOT / "backend" / "staymad"


def test_gold_directories_structure():
    assert GOLD_DIR.exists(), "eval/gold directory must exist"
    for split in ["train", "dev", "test"]:
        split_dir = GOLD_DIR / split
        assert split_dir.exists(), f"Split directory eval/gold/{split} must exist"
        assert split_dir.is_dir(), f"eval/gold/{split} must be a directory"


def test_gold_schema_valid_and_has_action_policy_violation():
    schema_path = GOLD_DIR / "schema.json"
    assert schema_path.exists(), "eval/gold/schema.json must exist"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert "required" in schema
    assert "labels" in schema["properties"]
    label_props = schema["properties"]["labels"]["properties"]

    # 6-field protocol per ADR-008 §3
    for field in [
        "event_id",
        "timeline_order",
        "location_canonical",
        "has_conflict",
        "expected_change",
        "action_policy",
    ]:
        assert field in label_props, f"Label field {field} must exist in schema"

    # A-5: action_policy_violation field
    assert "action_policy_violation" in label_props, (
        "action_policy_violation must be defined in schema (Finding A-5)"
    )


def test_gold_samples_conform_to_schema():
    schema_path = GOLD_DIR / "schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    for split in ["train", "dev", "test"]:
        split_dir = GOLD_DIR / split
        samples = list(split_dir.glob("*.json"))
        assert len(samples) > 0, f"Split {split} must contain gold sample files"
        for s_file in samples:
            with open(s_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for req in schema["required"]:
                assert req in data, f"{s_file.name} missing top-level field {req}"

            labels = data["labels"]
            for req_lbl in schema["properties"]["labels"]["required"]:
                assert req_lbl in labels, f"{s_file.name} missing label field {req_lbl}"

            assert isinstance(labels["action_policy_violation"], bool)


def test_blind_gold_test_path_isolation_from_application_code():
    """Ensure application code NEVER imports or reads from eval/gold/test/.

    Authority: ADR-008 §2, AGENTS.md, RSK-12.
    """
    forbidden_terms = ["eval/gold/test", "eval.gold.test"]

    for py_file in BACKEND_DIR.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in content, (
                f"Application file {py_file} violates gold set isolation by referencing '{term}'"
            )
