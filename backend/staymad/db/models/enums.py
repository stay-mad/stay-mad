"""Canonical enum definitions for Stay Mad data model.

Authority: ADR-003, ADR-004, ADR-005, ADR-006, docs/architecture/B-data-model.md
All enum values must follow documented specs and require an ADR to alter.
"""

from __future__ import annotations

import enum


class SourceType(str, enum.Enum):
    RSS = "RSS"
    API = "API"
    OFFICIAL_GOV = "OFFICIAL_GOV"
    SCRAPE = "SCRAPE"


class SourceTier(str, enum.Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"


class EventCategory(str, enum.Enum):
    DISASTER_AND_WEATHER = "DISASTER_AND_WEATHER"
    TRANSPORTATION_AND_INFRASTRUCTURE = "TRANSPORTATION_AND_INFRASTRUCTURE"
    GOVERNMENT_AND_PUBLIC_POLICY = "GOVERNMENT_AND_PUBLIC_POLICY"


class GeoLevel(str, enum.Enum):
    CITY = "CITY"
    PROVINCE = "PROVINCE"
    COUNTRY = "COUNTRY"
    CONTINENT = "CONTINENT"
    WORLD = "WORLD"


class ClaimStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    UNCONFIRMED = "UNCONFIRMED"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class TimelinePrecision(str, enum.Enum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    DAY = "DAY"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


class TimelineQualifier(str, enum.Enum):
    SEKITAR = "sekitar"
    SEBELUM = "sebelum"
    DIPERKIRAKAN = "diperkirakan"
    DILAPORKAN_PADA = "dilaporkan_pada"
    TEPAT = "tepat"


class EvidenceStatus(str, enum.Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT = "INSUFFICIENT"
    RETRACTED = "RETRACTED"


class VerificationLevel(str, enum.Enum):
    OFFICIAL_PRIMARY = "OFFICIAL_PRIMARY"
    INDEPENDENTLY_CORROBORATED = "INDEPENDENTLY_CORROBORATED"
    SINGLE_SOURCE = "SINGLE_SOURCE"


class ConfidenceBucket(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionabilityLevel(str, enum.Enum):
    ACTION_REQUIRED = "ACTION_REQUIRED"
    ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
    OPTIONAL = "OPTIONAL"
    INFORMATIONAL = "INFORMATIONAL"
    NO_IMMEDIATE_ACTION = "NO_IMMEDIATE_ACTION"


class DataMode(str, enum.Enum):
    LIVE = "LIVE"
    DEMO = "DEMO"
    DEGRADED = "DEGRADED"


class ChangeType(str, enum.Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    CORRECTED = "CORRECTED"
    RETRACTED = "RETRACTED"


class ChangeCategory(str, enum.Enum):
    AREA_CHANGE = "AREA_CHANGE"
    ALERT_STATUS = "ALERT_STATUS"
    ESCALATION = "ESCALATION"
    NUMERICAL = "NUMERICAL"
    NEWLY_CONFIRMED = "NEWLY_CONFIRMED"
    NEWLY_CONFLICTING = "NEWLY_CONFLICTING"


class EventClaimRole(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SUPPORTING = "SUPPORTING"
    CONFLICTING = "CONFLICTING"
    RETRACTED = "RETRACTED"


class ResolutionDecision(str, enum.Enum):
    SAME_EVENT = "SAME_EVENT"
    RELATED_EVENT = "RELATED_EVENT"
    SEPARATE_EVENT = "SEPARATE_EVENT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ActionSourceType(str, enum.Enum):
    OFFICIAL_EMERGENCY = "OFFICIAL_EMERGENCY"
    OFFICIAL_GOV = "OFFICIAL_GOV"
    OFFICIAL_HEALTH = "OFFICIAL_HEALTH"
    INFORMATIONAL = "INFORMATIONAL"


class ProcessingStage(str, enum.Enum):
    INGEST = "INGEST"
    EXTRACT = "EXTRACT"
    RESOLVE = "RESOLVE"
    SYNTHESIZE = "SYNTHESIZE"
    EVALUATE = "EVALUATE"


class RunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class JobType(str, enum.Enum):
    INGEST = "INGEST"
    EXTRACT = "EXTRACT"
    RESOLVE = "RESOLVE"
    SYNTHESIZE = "SYNTHESIZE"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class EventRelationType(str, enum.Enum):
    RELATED_TO = "RELATED_TO"
