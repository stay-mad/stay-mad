"""Pydantic schemas for Gemini LLM calls.

Authority: docs/architecture/C-gemini-architecture.md §53-C
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtractInput(BaseModel):
    """Input payload for Gemini Call Type 1: Extract.

    Per C-gemini-architecture.md: full_text is NOT sent to LLM for copyright & cost;
    only title + excerpt (<= 500 characters).
    """

    article_version_id: str
    source_id: str
    source_tier: str
    source_family: str
    title: str
    excerpt: str = Field(..., max_length=500)
    published_time: str | None = None
    updated_time: str | None = None
    source_url: str


class ExtractedClaim(BaseModel):
    """Atomic claim extracted by Gemini."""

    claim_text: str = Field(..., description="Atomic factual claim proposition")
    source_span: str = Field(
        ...,
        max_length=200,
        description="Verbatim substring (< 200 chars) from the excerpt/title as evidence",
    )
    speaker: str | None = Field(
        default=None, description="Attributed speaker if stated"
    )
    negation: bool = Field(default=False, description="True if statement is negated")
    numeric_value: float | None = Field(
        default=None, description="Extracted numerical metric if any"
    )
    unit: str | None = Field(
        default=None, description="Unit of measurement for numeric_value"
    )
    location_raw: str | None = Field(default=None, description="Raw location mentioned")
    event_time_raw: str | None = Field(
        default=None, description="Raw event time text mentioned"
    )
    event_time_qualifier: str | None = Field(
        default=None,
        description="Temporal qualifier (sekitar, diperkirakan, sebelum, dilaporkan_pada, tepat)",
    )
    event_time_precision: Literal["EXACT", "APPROXIMATE", "DAY", "RANGE", "UNKNOWN"] = (
        Field(
            default="UNKNOWN",
            description="Precision level of the extracted time",
        )
    )
    extraction_confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )


class ExtractedEntity(BaseModel):
    """Named entity extracted by Gemini."""

    name: str
    type: Literal["PERSON", "ORGANIZATION", "LOCATION", "INFRASTRUCTURE", "INSTITUTION"]
    canonical_form: str | None = None


class ExtractResponse(BaseModel):
    """Validated structured output from Gemini Call Type 1: Extract."""

    schema_version: str = "1.0"
    article_version_id: str
    suggested_category: Literal[
        "DISASTER_AND_WEATHER",
        "TRANSPORTATION_AND_INFRASTRUCTURE",
        "GOVERNMENT_AND_PUBLIC_POLICY",
        "UNKNOWN",
    ]
    claims: list[ExtractedClaim] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)
    primary_location_raw: str | None = None
    primary_event_time_raw: str | None = None
    insufficient_content: bool = False


class AnchorSummary(BaseModel):
    """Summary representation of canonical anchor event for Call Type 2: Adjudicate.

    Authority: docs/architecture/C-gemini-architecture.md §53-C
    """

    headline: str
    category: str
    primary_location: str | None = None
    time_window_start: str | None = None
    time_window_end: str | None = None
    representative_claims: list[str] = Field(default_factory=list)


class CandidateArticleInput(BaseModel):
    """Candidate article payload for Call Type 2: Adjudicate.

    Authority: docs/architecture/C-gemini-architecture.md §53-C
    """

    article_version_id: str
    source_tier: str
    source_family: str
    title: str
    excerpt: str = Field(..., max_length=500)
    published_time: str | None = None
    primary_location_raw: str | None = None
    primary_event_time_raw: str | None = None
    deterministic_score: float = 0.0
    deterministic_signals: dict[str, Any] = Field(default_factory=dict)
    top_claims: list[str] = Field(default_factory=list)


class AdjudicateInput(BaseModel):
    """Input payload for Gemini Call Type 2: Adjudicate.

    Authority: docs/architecture/C-gemini-architecture.md §53-C
    """

    schema_version: str = "1.0"
    processing_run_id: str
    anchor_event_id: str | None = None
    anchor_summary: AnchorSummary
    candidate_articles: list[CandidateArticleInput] = Field(default_factory=list)


class AdjudicateDecision(BaseModel):
    """Decision output for an individual candidate article.

    Canonical reason codes:
    LOC_MATCH, LOC_INCOMPATIBLE, TIME_WITHIN_WINDOW, TIME_INCOMPATIBLE,
    ENT_OVERLAP, CAT_MISMATCH, SOURCE_SYNDICATE, CORROBORATED, AMBIGUOUS,
    ADJUDICATION_FAILED.
    """

    article_version_id: str
    decision: Literal["SAME_EVENT", "RELATED_EVENT", "SEPARATE_EVENT", "NEEDS_REVIEW"]
    decision_reason_codes: list[str] = Field(default_factory=list)
    evidence_claim_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: str | None = None


class AdjudicateResponse(BaseModel):
    """Validated structured output from Gemini Call Type 2: Adjudicate.

    Authority: docs/architecture/C-gemini-architecture.md §53-C
    """

    schema_version: str = "1.0"
    decisions: list[AdjudicateDecision] = Field(default_factory=list)
    suggested_event_headline: str | None = None


# ---------------------------------------------------------------------------
# Call Type 3: Synthesize
# Authority: docs/architecture/C-gemini-architecture.md §53-C
# ---------------------------------------------------------------------------


class SynthesizeClaimInput(BaseModel):
    """Claim representation sent to Gemini for narrative synthesis."""

    claim_id: str
    claim_text: str
    source_span: str = Field(default="", max_length=200)
    source_tier: str = "TIER_2"
    source_family: str = "UNKNOWN"
    event_time: str | None = None
    event_time_qualifier: str | None = None
    extraction_confidence: float = 0.9
    role: Literal["PRIMARY", "SUPPORTING", "CONFLICTING", "RETRACTED"] = "PRIMARY"


class SynthesizeConflictInput(BaseModel):
    """Conflict context between claims sent for synthesis."""

    field_name: str
    value_a: str
    value_b: str
    claim_a_id: str
    claim_b_id: str


class SynthesizeLocationInput(BaseModel):
    """Location information for synthesis payload."""

    city: str | None = None
    province: str | None = None
    country: str = "Indonesia"


class SynthesizeInput(BaseModel):
    """Input payload for Gemini Call Type 3: Synthesize.

    Authority: docs/architecture/C-gemini-architecture.md §53-C
    """

    schema_version: str = "1.0"
    processing_run_id: str
    event_id: str
    category: str
    primary_location: SynthesizeLocationInput | None = None
    time_window_start: str | None = None
    time_window_end: str | None = None
    output_language: str = "id"
    claims: list[SynthesizeClaimInput] = Field(default_factory=list)
    conflicts: list[SynthesizeConflictInput] = Field(default_factory=list)
    previous_snapshot_id: str | None = None
    actionability_gate_passed: bool = False


class GroundedNarrativePoint(BaseModel):
    """Factual narrative section strictly grounded by evidence claims."""

    text: str | None = None
    evidence_claim_ids: list[str] = Field(default_factory=list)


class SuggestedActionItem(BaseModel):
    """Action recommendation derived from official instructions."""

    action_level: Literal[
        "ACTION_REQUIRED",
        "ACTION_RECOMMENDED",
        "OPTIONAL",
        "INFORMATIONAL",
        "NO_IMMEDIATE_ACTION",
    ]
    action_text: str
    requires_official_source: bool = True
    evidence_claim_ids: list[str] = Field(default_factory=list)


class SynthesizeResponse(BaseModel):
    """Validated structured output from Gemini Call Type 3: Synthesize.

    Authority: docs/architecture/C-gemini-architecture.md §53-C
    """

    schema_version: str = "1.0"
    headline: str = Field(..., max_length=150)
    what_happened: GroundedNarrativePoint
    why_it_matters: GroundedNarrativePoint | None = None
    who_is_affected: GroundedNarrativePoint | None = None
    what_is_unknown: GroundedNarrativePoint | None = None
    conflict_summary: GroundedNarrativePoint | None = None
    suggested_actions: list[SuggestedActionItem] = Field(default_factory=list)
    insufficient_evidence: bool = False
