"""Unit tests for mathematical evaluation metrics engine.

Validates Pairwise, B³, Timeline, Location, Attribution, Conflict, Change,
and Safety Gating metrics formulas against known ground-truth scenarios.

Authority: docs/architecture/I-evaluation-framework.md (§53-I), DEC-0006, ADR-008.
"""

from __future__ import annotations

import pytest

from backend.staymad.jobs.eval_metrics import (
    compute_attribution_metrics,
    compute_bcubed_clustering,
    compute_change_metrics,
    compute_conflict_metrics,
    compute_hierarchical_location_accuracy,
    compute_pairwise_clustering,
    compute_safety_metrics,
    compute_temporal_qualifier_preservation,
    compute_timeline_ordering,
    compute_timestamp_coverage,
)

# ── Clustering Metrics Tests ─────────────────────────────────────────────────


def test_pairwise_clustering_perfect_match():
    gold = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}
    pred = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}

    res = compute_pairwise_clustering(gold, pred)
    assert res["pairwise_precision"] == 1.0
    assert res["pairwise_recall"] == 1.0
    assert res["pairwise_f1"] == 1.0


def test_pairwise_clustering_over_merged():
    # Gold has two clusters, prediction merged everything into one
    gold = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}
    pred = {"a": "E1", "b": "E1", "c": "E1", "d": "E1"}

    res = compute_pairwise_clustering(gold, pred)
    # Pairs: (a,b)=TP, (c,d)=TP, (a,c)=FP, (a,d)=FP, (b,c)=FP, (b,d)=FP. FN=0.
    # Total pairs = 6. TP = 2, FP = 4, FN = 0.
    # Precision = 2/6 = 0.3333, Recall = 2/2 = 1.0
    assert res["pairwise_recall"] == 1.0
    assert res["pairwise_precision"] == pytest.approx(2 / 6, abs=1e-3)
    assert res["pairwise_f1"] == pytest.approx(0.5, abs=1e-3)


def test_pairwise_clustering_over_split():
    # Gold has two clusters, prediction split each item into its own cluster
    gold = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}
    pred = {"a": "P1", "b": "P2", "c": "P3", "d": "P4"}

    res = compute_pairwise_clustering(gold, pred)
    # No predicted pairs together -> TP = 0, FP = 0, FN = 2
    assert res["pairwise_precision"] == 0.0
    assert res["pairwise_recall"] == 0.0
    assert res["pairwise_f1"] == 0.0


def test_bcubed_clustering_perfect_match():
    gold = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}
    pred = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}

    res = compute_bcubed_clustering(gold, pred)
    assert res["b3_precision"] == 1.0
    assert res["b3_recall"] == 1.0
    assert res["b3_f1"] == 1.0


def test_bcubed_clustering_partial_overlap():
    # Gold: {a, b}, {c, d}
    # Pred: {a, b, c}, {d}
    # For a: Pred={a,b,c}, Gold={a,b} -> P=2/3, R=2/2=1.0
    # For b: Pred={a,b,c}, Gold={a,b} -> P=2/3, R=2/2=1.0
    # For c: Pred={a,b,c}, Gold={c,d} -> P=1/3, R=1/2=0.5
    # For d: Pred={d}, Gold={c,d} -> P=1/1=1.0, R=1/2=0.5
    gold = {"a": "E1", "b": "E1", "c": "E2", "d": "E2"}
    pred = {"a": "P1", "b": "P1", "c": "P1", "d": "P2"}

    res = compute_bcubed_clustering(gold, pred)
    expected_p = (2 / 3 + 2 / 3 + 1 / 3 + 1.0) / 4.0
    expected_r = (1.0 + 1.0 + 0.5 + 0.5) / 4.0
    expected_f1 = 2 * expected_p * expected_r / (expected_p + expected_r)

    assert res["b3_precision"] == pytest.approx(expected_p, abs=1e-3)
    assert res["b3_recall"] == pytest.approx(expected_r, abs=1e-3)
    assert res["b3_f1"] == pytest.approx(expected_f1, abs=1e-3)


# ── Timeline Metrics Tests ───────────────────────────────────────────────────


def test_timeline_ordering_perfect_and_inverted():
    gold_order = {"art1": 1, "art2": 2, "art3": 3}
    pred_order_good = {"art1": 10, "art2": 20, "art3": 30}
    pred_order_bad = {"art1": 30, "art2": 20, "art3": 10}

    res_good = compute_timeline_ordering(gold_order, pred_order_good)
    assert res_good["ordering_f1"] == 1.0

    res_bad = compute_timeline_ordering(gold_order, pred_order_bad)
    assert res_bad["ordering_f1"] == 0.0


def test_timestamp_coverage_calculation():
    entries = [
        {"event_time": "2026-10-10T08:00:00Z"},
        {"event_time": "2026-10-10T09:00:00Z"},
        {"event_time": None},
        {"event_time": ""},
    ]
    coverage = compute_timestamp_coverage(entries)
    assert coverage == 0.5


def test_temporal_qualifier_preservation():
    items = [
        {
            "content_text": "Banjir terjadi sekitar pukul 08:00 WIB.",
            "description": "Genangan tercatat sekitar jam 08:00 WIB",
            "time_precision": "approximate",
        },
        {
            "content_text": "Erupsi terjadi dini hari tadi.",
            "description": "Erupsi dini hari",
            "time_precision": "part_of_day",
        },
        {
            "content_text": "Hujan deras mengguyur siang ini.",
            "description": "Hujan siang ini",
            "time_precision": "relative",
        },
    ]
    rate = compute_temporal_qualifier_preservation(items)
    assert rate == 1.0


# ── Location & Attribution Tests ─────────────────────────────────────────────


def test_location_accuracy_calculation():
    gold_locs = {
        "art1": "Jakarta Timur, DKI Jakarta",
        "art2": "Sleman, DI Yogyakarta",
    }
    pred_locs_perfect = {
        "art1": {"city": "Jakarta Timur", "province": "DKI Jakarta"},
        "art2": {"city": "Sleman", "province": "DI Yogyakarta"},
    }
    pred_locs_partial = {
        "art1": {"city": "Jakarta Selatan", "province": "DKI Jakarta"},
        "art2": {"city": "Sleman", "province": "DI Yogyakarta"},
    }

    res_perfect = compute_hierarchical_location_accuracy(gold_locs, pred_locs_perfect)
    assert res_perfect["city_accuracy"] == 1.0
    assert res_perfect["province_accuracy"] == 1.0
    assert res_perfect["hierarchical_f1"] == 1.0

    res_partial = compute_hierarchical_location_accuracy(gold_locs, pred_locs_partial)
    assert res_partial["province_accuracy"] == 1.0
    assert res_partial["city_accuracy"] == 0.5
    assert res_partial["hierarchical_f1"] == pytest.approx(2 / 3, abs=1e-3)


def test_attribution_metrics_calculation():
    claims = [
        {
            "verbatim_quote": "Air setinggi 70 cm.",
            "evidence_claim_ids": ["c1"],
            "source_domain": "antaranews.com",
        },
        {
            "verbatim_quote": "",
            "evidence_claim_ids": ["c2"],
            "source_domain": "bpbd.jakarta.go.id",
        },
        {
            "verbatim_quote": "",
            "evidence_claim_ids": [],
            "source_domain": "republika.co.id",
        },
    ]
    res = compute_attribution_metrics(claims)
    # 2 out of 3 grounded
    assert res["grounded_coverage"] == pytest.approx(2 / 3, abs=1e-3)
    assert res["unsupported_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert res["source_attribution_accuracy"] == 1.0


# ── Conflict & Change Detection Tests ────────────────────────────────────────


def test_conflict_metrics_calculation():
    gold = {"art1": True, "art2": True, "art3": False, "art4": False}
    pred = {"art1": True, "art2": False, "art3": True, "art4": False}
    # TP: art1 (1). FP: art3 (1). FN: art2 (1). TN: art4 (1).
    res = compute_conflict_metrics(gold, pred)
    assert res["precision"] == 0.5
    assert res["recall"] == 0.5
    assert res["f1"] == 0.5


def test_change_metrics_calculation():
    gold = {"art1": True, "art2": False, "art3": False}
    pred = {"art1": True, "art2": False, "art3": False}
    wording_only = ["art2", "art3"]

    res = compute_change_metrics(gold, pred, wording_only_keys=wording_only)
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["no_change_specificity"] == 1.0


# ── Safety Gating Tests ──────────────────────────────────────────────────────


def test_safety_metrics_strict_guarantees():
    # Finding A-5 & ADR-006: Unsupported Action Rate must be strictly 0.00
    gold_violations = {
        "art_safe_01": False,
        "art_safe_02": False,
        "art_malicious_01": True,
        "art_unverified_02": True,
    }
    # System safely suppresses unverified actions into NO_IMMEDIATE_ACTION / INFORMATIONAL
    pred_actions_safe = {
        "art_safe_01": "ACTION_REQUIRED",
        "art_safe_02": "INFORMATIONAL",
        "art_malicious_01": "NO_IMMEDIATE_ACTION",
        "art_unverified_02": "INFORMATIONAL",
    }
    res_safe = compute_safety_metrics(
        gold_policy_violations=gold_violations,
        pred_actions=pred_actions_safe,
        injection_samples=["art_malicious_01"],
        injection_results={"art_malicious_01": False},  # Injection blocked
    )
    assert res_safe["unsupported_action_rate"] == 0.0
    assert res_safe["injection_failure_rate"] == 0.0

    # Test failure detection: If system admitted an unsupported action, rate > 0
    pred_actions_leaked = {
        "art_malicious_01": "ACTION_REQUIRED",  # Violation leaked!
        "art_unverified_02": "INFORMATIONAL",
    }
    res_leaked = compute_safety_metrics(
        gold_policy_violations=gold_violations,
        pred_actions=pred_actions_leaked,
        injection_samples=["art_malicious_01"],
        injection_results={"art_malicious_01": True},  # Injection succeeded
    )
    assert res_leaked["unsupported_action_rate"] == 0.5
    assert res_leaked["injection_failure_rate"] == 1.0
