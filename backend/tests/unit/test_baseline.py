"""Unit tests for Stage 00 Delivery Framing Baseline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_config_sources_valid():
    sources_path = REPO_ROOT / "config" / "sources.yaml"
    assert sources_path.exists(), "config/sources.yaml must exist"

    with open(sources_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "sources" in data
    sources = data["sources"]
    assert len(sources) >= 5, "At least 5 verified sources required"

    domains = set()
    for src in sources:
        assert "id" in src
        assert "domain" in src
        assert "tier" in src
        assert "source_family" in src
        assert src["tier"] in (1, 2)
        domains.add(src["domain"])

    # Ensure official emergency/weather agencies exist
    assert "data.bmkg.go.id" in domains
    assert "bpbd.jakarta.go.id" in domains
    assert "bnpb.go.id" in domains
    assert "setkab.go.id" in domains
    assert "antaranews.com" in domains

    # Ensure C-2 sources exist per ADR-006 & docs/sources.md
    assert "tempo.co" in domains
    assert "kompas.com" in domains
    assert "cnbcindonesia.com" in domains
    assert len(sources) == 11, f"Expected 11 synchronized sources, got {len(sources)}"


def test_config_resolver_valid():
    resolver_path = REPO_ROOT / "config" / "resolver.yaml"
    assert resolver_path.exists(), "config/resolver.yaml must exist"

    with open(resolver_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "entity_resolution" in data
    assert "event_resolution" in data
    assert data["event_resolution"]["time_window_hours"] > 0


def test_config_confidence_valid():
    confidence_path = REPO_ROOT / "config" / "confidence.yaml"
    assert confidence_path.exists(), "config/confidence.yaml must exist"

    with open(confidence_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    weights = data.get("weights", {})
    total_weight = sum(weights.values())
    assert pytest.approx(total_weight, 0.01) == 1.0, "Weights must sum to 1.0"


def test_seed_demo_23_articles_clusters_and_counts():
    fixture_path = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"
    assert fixture_path.exists(), "seed_demo_23.json must exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    clusters = data.get("clusters", [])

    assert len(articles) == 23, f"Expected exactly 23 articles, got {len(articles)}"
    assert len(clusters) == 4, f"Expected exactly 4 clusters, got {len(clusters)}"

    # Check cluster counts: 8 (Flood), 5 (Volcano), 4 (Transport), 6 (Policy)
    counts_by_cluster = {}
    for art in articles:
        cid = art["cluster_id"]
        counts_by_cluster[cid] = counts_by_cluster.get(cid, 0) + 1

    assert counts_by_cluster["cluster_a_flood"] == 8
    assert counts_by_cluster["cluster_b_volcano"] == 5
    assert counts_by_cluster["cluster_c_transport"] == 4
    assert counts_by_cluster["cluster_d_policy"] == 6


def test_seed_demo_categories_bounded_mvp():
    fixture_path = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    allowed_categories = {
        "disaster_and_weather",
        "transportation_and_infrastructure",
        "government_and_public_policy",
    }

    for art in data["articles"]:
        cat = art["category"]
        assert cat in allowed_categories, (
            f"Category '{cat}' is outside 3 bounded MVP categories"
        )

    # Verify DEC-0007: policy cluster mapped to government_and_public_policy
    policy_articles = [
        a for a in data["articles"] if a["cluster_id"] == "cluster_d_policy"
    ]
    for p in policy_articles:
        assert p["category"] == "government_and_public_policy"


def test_seed_demo_mandatory_edge_cases():
    fixture_path = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_flags = set()
    for art in data["articles"]:
        for flag in art.get("edge_case_flags", []):
            all_flags.add(flag)

    expected_edge_cases = {
        "syndication_duplicate",
        "source_family_grouping",
        "number_conflict",
        "official_update",
        "relative_time",
        "multi_event_article",
        "different_day_similar_event",
        "retraction",
        "malicious_prompt_injection",
    }

    missing = expected_edge_cases - all_flags
    assert not missing, f"Missing required edge cases: {missing}"


def test_seed_demo_acceptance_scenarios_mapping():
    fixture_path = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenario_numbers = {art.get("acceptance_scenario") for art in data["articles"]}
    # Scenarios 1 to 6 mapped directly to article triggers
    for s in range(1, 7):
        assert s in scenario_numbers, f"Acceptance scenario {s} must be mapped"


def test_prompt_injection_safety_fixture():
    fixture_path = REPO_ROOT / "eval" / "fixtures" / "seed_demo_23.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles_by_id = {a["article_id"]: a for a in data["articles"]}
    art_inj = articles_by_id["art_demo_07"]

    # Verify the injection string exists in the test fixture
    assert "SYSTEM INSTRUCTION OVERRIDE" in art_inj["content_text"]
    assert art_inj["expected_role"] == "malicious_injection"
    assert art_inj["ground_truth_event_id"] == "REJECTED_OR_ISOLATED"
