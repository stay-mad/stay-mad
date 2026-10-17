"""Unit tests for EventSnapshot evidence grounding persistence.

Authority: DIM7-001, §53-C, DEC-0008, Addendum §5.2
"""

from __future__ import annotations

from backend.staymad.db.models.event import EventSnapshot


def test_evidence_grounding_persistence():
    """Test that evidence_claim_ids are persisted to EventSnapshot."""
    snapshot = EventSnapshot(
        event_id="evt_123",
        processing_run_id="run_456",
        what_happened="Banjir melanda 7 kecamatan di Jakarta Timur",
        what_happened_evidence_claim_ids=["claim_001", "claim_002", "claim_007"],
        why_it_matters="Ribuan warga terdampak dan jalur transportasi utama terputus",
        why_it_matters_evidence_claim_ids=["claim_003", "claim_005"],
    )

    assert snapshot.what_happened_evidence_claim_ids == [
        "claim_001",
        "claim_002",
        "claim_007",
    ]
    assert snapshot.why_it_matters_evidence_claim_ids == ["claim_003", "claim_005"]
    assert len(snapshot.what_happened_evidence_claim_ids) == 3


def test_empty_evidence_defaults_to_empty_list():
    """Test that missing evidence_claim_ids defaults to empty list."""
    snapshot = EventSnapshot(
        event_id="evt_123",
        what_happened="Some text without evidence",
    )

    assert snapshot.what_happened_evidence_claim_ids == []
