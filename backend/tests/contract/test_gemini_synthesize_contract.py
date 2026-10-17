"""Contract tests for Gemini Call Type 3: Synthesize.

Authority: docs/architecture/C-gemini-architecture.md §53-C, DEC-0004, DEC-0008
"""

from __future__ import annotations

import uuid

from backend.staymad.llm.base import (
    PROMPT_VERSION_SYNTHESIZE,
    SCHEMA_VERSION_SYNTHESIZE,
)
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.llm.schemas import (
    SynthesizeClaimInput,
    SynthesizeInput,
    SynthesizeLocationInput,
    SynthesizeResponse,
)


def test_synthesize_schema_contract_conformance():
    """Verify SynthesizeResponse schema complies with C-gemini-architecture.md §53-C."""
    schema = SynthesizeResponse.model_json_schema()

    assert "properties" in schema
    assert "headline" in schema["properties"]
    assert "what_happened" in schema["properties"]
    assert "why_it_matters" in schema["properties"]
    assert "who_is_affected" in schema["properties"]
    assert "what_is_unknown" in schema["properties"]
    assert "conflict_summary" in schema["properties"]
    assert "suggested_actions" in schema["properties"]
    assert "insufficient_evidence" in schema["properties"]


def test_deterministic_client_synthesizes_grounded_response():
    """Verify DeterministicGeminiClient generates structured, grounded synthesis with claim citations."""
    client = DeterministicGeminiClient()

    cid1 = str(uuid.uuid4())
    cid2 = str(uuid.uuid4())
    cid3 = str(uuid.uuid4())

    payload = SynthesizeInput(
        schema_version=SCHEMA_VERSION_SYNTHESIZE,
        processing_run_id=str(uuid.uuid4()),
        event_id=str(uuid.uuid4()),
        category="DISASTER_AND_WEATHER",
        primary_location=SynthesizeLocationInput(
            city="Jakarta Timur",
            province="DKI Jakarta",
            country="Indonesia",
        ),
        time_window_start="2026-10-10T01:00:00Z",
        output_language="id",
        claims=[
            SynthesizeClaimInput(
                claim_id=cid1,
                claim_text="Hujan deras menyebabkan luapan Kali Ciliwung merendam permukiman di Jakarta Timur.",
                source_span="luapan Kali Ciliwung merendam permukiman",
                source_tier="TIER_1",
                source_family="LKBN_ANTARA",
                event_time="2026-10-10T01:00:00Z",
                role="PRIMARY",
            ),
            SynthesizeClaimInput(
                claim_id=cid2,
                claim_text="Ketinggian air mencapai antara 40 hingga 80 cm merendam ratusan rumah warga.",
                source_span="ketinggian air mencapai antara 40 hingga 80 cm",
                source_tier="TIER_2",
                source_family="TRANSMEDIA",
                role="PRIMARY",
            ),
            SynthesizeClaimInput(
                claim_id=cid3,
                claim_text="BPBD DKI menginstruksikan warga kelompok rentan segera melakukan evakuasi mandiri.",
                source_span="menginstruksikan warga kelompok rentan segera melakukan evakuasi mandiri",
                source_tier="TIER_1",
                source_family="GOV_BPBD_DKI",
                role="PRIMARY",
            ),
        ],
        conflicts=[],
    )

    resp = client.synthesize(payload)

    assert isinstance(resp, SynthesizeResponse)
    assert not resp.insufficient_evidence
    assert len(resp.headline) <= 120
    assert resp.what_happened.text
    # Factual grounding: what_happened MUST cite evidence_claim_ids per DEC-0008
    assert len(resp.what_happened.evidence_claim_ids) > 0
    assert cid1 in resp.what_happened.evidence_claim_ids

    # what_is_unknown must have empty evidence_claim_ids per §53-C
    assert resp.what_is_unknown is not None
    assert len(resp.what_is_unknown.evidence_claim_ids) == 0

    # Official emergency action generated from BPBD claim
    assert len(resp.suggested_actions) > 0
    action = resp.suggested_actions[0]
    assert action.action_level == "ACTION_REQUIRED"
    assert action.requires_official_source is True
    assert cid3 in action.evidence_claim_ids


def test_deterministic_client_insufficient_content():
    """Verify synthesize behavior when no claims are provided."""
    client = DeterministicGeminiClient()
    payload = SynthesizeInput(
        schema_version=SCHEMA_VERSION_SYNTHESIZE,
        processing_run_id=str(uuid.uuid4()),
        event_id=str(uuid.uuid4()),
        category="DISASTER_AND_WEATHER",
        claims=[],
    )

    resp = client.synthesize(payload)
    assert resp.insufficient_evidence is True
    assert resp.what_happened.text == "Not enough information available."
    assert resp.what_happened.evidence_claim_ids == []


def test_synthesize_cache_key_determinism():
    """Verify cache key generation is deterministic and sensitive to claim IDs."""
    client = DeterministicGeminiClient(
        prompt_version=PROMPT_VERSION_SYNTHESIZE,
        schema_version=SCHEMA_VERSION_SYNTHESIZE,
    )
    event_id = str(uuid.uuid4())
    c1, c2 = str(uuid.uuid4()), str(uuid.uuid4())

    key1 = client.compute_synthesize_cache_key([c1, c2], event_id)
    key2 = client.compute_synthesize_cache_key([c2, c1], event_id)
    # Order of claims should not change cache key because sorted() is used
    assert key1 == key2

    key3 = client.compute_synthesize_cache_key([c1], event_id)
    assert key1 != key3
