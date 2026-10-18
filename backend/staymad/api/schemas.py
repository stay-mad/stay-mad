"""Pydantic schemas for Stay Mad API.

Directly implements schemas defined in docs/contracts/openapi.yaml.
Authority: docs/contracts/openapi.yaml (OpenAPI 3.1), ADR-003, ADR-004, ADR-005.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Enums (OpenAPI Components) ────────────────────────────────────────────────


class EventCategory(str, Enum):
    DISASTER_AND_WEATHER = "disaster_and_weather"
    TRANSPORTATION_AND_INFRASTRUCTURE = "transportation_and_infrastructure"
    GOVERNMENT_AND_PUBLIC_POLICY = "government_and_public_policy"


class DataMode(str, Enum):
    LIVE = "live"
    DEMO = "demo"
    DEGRADED = "degraded"


class GeoLevel(str, Enum):
    CITY = "city"
    PROVINCE = "province"
    COUNTRY = "country"
    CONTINENT = "continent"
    WORLD = "world"


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT = "INSUFFICIENT"
    RETRACTED = "RETRACTED"


class VerificationLevel(str, Enum):
    OFFICIAL_PRIMARY = "OFFICIAL_PRIMARY"
    INDEPENDENTLY_CORROBORATED = "INDEPENDENTLY_CORROBORATED"
    SINGLE_SOURCE = "SINGLE_SOURCE"


class ConfidenceBucket(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionabilityLevel(str, Enum):
    ACTION_REQUIRED = "ACTION_REQUIRED"
    ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
    OPTIONAL = "OPTIONAL"
    INFORMATIONAL = "INFORMATIONAL"
    NO_IMMEDIATE_ACTION = "NO_IMMEDIATE_ACTION"


class TimelinePrecision(str, Enum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    DAY = "DAY"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


class TimelineQualifier(str, Enum):
    SEKITAR = "sekitar"
    SEBELUM = "sebelum"
    DIPERKIRAKAN = "diperkirakan"
    DILAPORKAN_PADA = "dilaporkan_pada"
    TEPAT = "tepat"


class ChangeType(str, Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    CORRECTED = "CORRECTED"
    RETRACTED = "RETRACTED"


class ChangeCategory(str, Enum):
    AREA_CHANGE = "AREA_CHANGE"
    ALERT_STATUS = "ALERT_STATUS"
    ESCALATION = "ESCALATION"
    NUMERICAL = "NUMERICAL"
    NEWLY_CONFIRMED = "NEWLY_CONFIRMED"
    NEWLY_CONFLICTING = "NEWLY_CONFLICTING"


class ClaimStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    UNCONFIRMED = "UNCONFIRMED"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class ResolutionDecision(str, Enum):
    SAME_EVENT = "SAME_EVENT"
    RELATED_EVENT = "RELATED_EVENT"
    SEPARATE_EVENT = "SEPARATE_EVENT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SourceTier(str, Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"


# ── Core Entity Schemas ───────────────────────────────────────────────────────


class Location(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    city: str | None = None
    district: str | None = None
    province: str | None = None
    country: str = "Indonesia"
    geo_level: GeoLevel
    canonical_name: str


class ConfidenceComponents(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_quality: float = 0.0
    corroboration: float = 0.0
    claim_consistency: float = 0.0
    official_confirmation: float = 0.0
    temporal_consistency: float = 0.0


class ConfidenceSignals(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_bucket: ConfidenceBucket
    evidence_status: EvidenceStatus
    verification_level: VerificationLevel
    components: ConfidenceComponents | None = None
    signals_text: list[str] = Field(default_factory=list)


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: EventCategory
    headline: str
    primary_location: Location | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    confidence_signals: ConfidenceSignals
    importance_score: float = Field(..., ge=0.0, le=1.0)
    urgency_score: float = Field(..., ge=0.0, le=1.0)
    actionability_level: ActionabilityLevel
    snapshot_id: uuid.UUID
    data_mode: DataMode
    last_processed_at: datetime
    processing_run_id: uuid.UUID


class EventSummaryStats(BaseModel):
    total: int = 0
    need_to_know: int = 0
    official_primary: int = 0
    conflicts: int = 0


class EventListResponse(BaseModel):
    events: list[EventSummary]
    total: int
    limit: int
    offset: int
    data_mode: DataMode
    summary_stats: EventSummaryStats | None = None


class EvidenceField(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str | None = None
    evidence_claim_ids: list[uuid.UUID] = Field(default_factory=list)


class ActionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_level: ActionabilityLevel
    action_text: str
    evidence_claim_ids: list[uuid.UUID] = Field(default_factory=list)


class EventDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    snapshot_id: uuid.UUID
    category: EventCategory
    headline: str
    primary_location: Location | None = None
    time_window_start: datetime | None = None
    what_happened: EvidenceField
    why_it_matters: EvidenceField | None = None
    who_is_affected: EvidenceField | None = None
    what_is_unknown: EvidenceField | None = None
    conflict_summary: EvidenceField | None = None
    actions: list[ActionItem] = Field(default_factory=list)
    confidence_signals: ConfidenceSignals
    importance_score: float = Field(..., ge=0.0, le=1.0)
    urgency_score: float = Field(..., ge=0.0, le=1.0)
    actionability_level: ActionabilityLevel
    data_mode: DataMode
    last_processed_at: datetime
    processing_run_id: uuid.UUID


class TimelineEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_time: datetime | None = None
    display_time: str | None = None
    event_time_precision: TimelinePrecision
    event_time_qualifier: TimelineQualifier | str | None = None
    description: str
    evidence_claim_ids: list[uuid.UUID] = Field(default_factory=list)
    order_index: int


class TimelineResponse(BaseModel):
    event_id: uuid.UUID
    snapshot_id: uuid.UUID
    entries: list[TimelineEntry]
    processing_run_id: uuid.UUID


class SourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: uuid.UUID
    name: str
    source_tier: SourceTier
    source_family: str
    article_url: str
    published_time: datetime | None = None
    article_version_id: uuid.UUID


class SourcesResponse(BaseModel):
    event_id: uuid.UUID
    sources: list[SourceItem]
    unique_source_families: int
    processing_run_id: uuid.UUID


class ChangeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    change_type: ChangeType
    change_category: ChangeCategory | None = None
    field_name: str | None = None
    before_value: str | None = None
    after_value: str | None = None
    evidence_claim_ids: list[uuid.UUID] = Field(default_factory=list)


class ChangesResponse(BaseModel):
    event_id: uuid.UUID
    from_snapshot_id: uuid.UUID | None = None
    to_snapshot_id: uuid.UUID
    changes: list[ChangeItem]
    material_change_count: int


class ConflictItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_name: str
    claim_a_id: uuid.UUID
    claim_b_id: uuid.UUID
    value_a: str
    value_b: str
    context: str | None = None
    resolved: bool


class AnalysisResponse(BaseModel):
    event_id: uuid.UUID
    snapshot_id: uuid.UUID
    conflicts: list[ConflictItem]
    confidence_signals: ConfidenceSignals
    claim_count: int
    conflicting_claim_count: int
    processing_run_id: uuid.UUID


class ProcessingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    snapshot_id: uuid.UUID
    processing_run_id: uuid.UUID
    correlation_id: str | None = None
    articles_analyzed: int
    claims_extracted: int
    candidate_events_considered: int
    timeline_entries: int
    conflicts_detected: int
    decision_reason_codes: list[str] = Field(default_factory=list)
    resolution_tier_used: str = "TIER_2"
    confidence_signals: ConfidenceSignals
    model_version: str
    prompt_version: str
    schema_version: str
    last_processed_at: datetime
    data_mode: DataMode


class LocationsResponse(BaseModel):
    locations: list[Location]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    database: Literal["connected", "disconnected"]
    gemini: Literal["reachable", "unreachable", "not_checked"] = "not_checked"
    fixture_mode: bool
    environment: Literal["production", "staging", "development", "test"]
    version: str = "0.1.0"
    details: str | None = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Any = None


class IngestJobRequest(BaseModel):
    source: str = "all"
    limit: int = 3
    db_url: str | None = None


class JobIngestResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    job_id: str
    message: str = "Live data ingestion job queued successfully in background."
    source: str = "all"
    limit: int = 3
    created_at: datetime


class JobDetailResponse(BaseModel):
    job_id: str
    status: str
    source: str
    limit: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: dict[str, Any] | None = None
    error: str | None = None
