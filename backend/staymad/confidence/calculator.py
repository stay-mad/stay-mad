"""Deterministic Confidence Scoring Calculator.

Authority: docs/architecture/F-confidence-algorithm.md (§53-F), ADR-004, DEC-0008
Single source of truth: config/confidence.yaml
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.staymad.confidence.config import ConfidenceConfig
from backend.staymad.db.models.enums import (
    ConfidenceBucket,
    EvidenceStatus,
    VerificationLevel,
)

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim
    from backend.staymad.db.models.conflict import Conflict


@dataclass
class ConfidenceResult:
    """Outcome of confidence scoring with component breakdown and derived enums."""

    confidence_score: float
    confidence_bucket: ConfidenceBucket
    evidence_status: EvidenceStatus
    verification_level: VerificationLevel
    components: dict[str, float]


def calculate_confidence(
    claims: list[Claim],
    conflicts: list[Conflict] | None = None,
    is_retracted: bool = False,
    config: ConfidenceConfig | None = None,
) -> ConfidenceResult:
    """Calculate deterministic confidence_score per §53-F and map to status enums.

    Components:
    1. source_quality_score (w=0.30)
    2. corroboration_score (w=0.25)
    3. claim_consistency_score (w=0.20)
    4. official_confirmation_score (w=0.15)
    5. temporal_consistency_score (w=0.10)
    """
    cfg = config or ConfidenceConfig.load()
    conflicts = conflicts or []

    if not claims:
        return ConfidenceResult(
            confidence_score=0.0,
            confidence_bucket=ConfidenceBucket.LOW,
            evidence_status=EvidenceStatus.INSUFFICIENT,
            verification_level=VerificationLevel.SINGLE_SOURCE,
            components={
                "source_quality": 0.0,
                "corroboration": 0.0,
                "claim_consistency": 0.0,
                "official_confirmation": 0.0,
                "temporal_consistency": 0.0,
            },
        )

    # 1. source_quality_score (§53-F §2.1)
    # Check strongest source tier among claims
    source_quality_score = 0.40
    for c in claims:
        src = c.source
        fam = src.source_family if src else ""
        tier = (
            (
                src.source_tier.value
                if hasattr(src.source_tier, "value")
                else str(src.source_tier)
            ).upper()
            if src
            else ""
        )
        if "TIER_1" in tier or tier == "1":
            if (
                fam.startswith("GOV_")
                or "BMKG" in fam
                or "BPBD" in fam
                or "BNPB" in fam
                or "SETKAB" in fam
            ):
                source_quality_score = max(source_quality_score, 1.0)
            elif "ANTARA" in fam or "LKBN" in fam:
                source_quality_score = max(source_quality_score, 0.85)
            else:
                source_quality_score = max(source_quality_score, 0.85)
        elif "TIER_2" in tier or tier == "2":
            source_quality_score = max(source_quality_score, 0.65)

    # 2. corroboration_score (§53-F §2.2)
    # Unique source families
    unique_families = {
        c.source.source_family
        for c in claims
        if c.source and c.source.source_family and c.source.source_family != "UNKNOWN"
    }
    corroboration_score = min(
        1.0, len(unique_families) / max(1, cfg.corroboration_max_families)
    )

    # 3. claim_consistency_score (§53-F §2.3)
    unresolved_conflicts = [cf for cf in conflicts if not cf.resolved]
    if not unresolved_conflicts:
        claim_consistency_score = 1.0
    else:
        # Each conflict involves 2 claims
        conflict_ratio = (len(unresolved_conflicts) * 2) / max(1, len(claims))
        claim_consistency_score = max(0.0, 1.0 - (conflict_ratio * 2.0))

    # 4. official_confirmation_score (§53-F §2.4)
    has_official_gov = any(
        (
            c.source
            and c.source.source_family.startswith("GOV_")
            and (
                "TIER_1"
                in (
                    c.source.source_tier.value
                    if hasattr(c.source.source_tier, "value")
                    else str(c.source.source_tier)
                ).upper()
                or str(c.source.source_tier) == "1"
            )
        )
        for c in claims
    )
    official_confirmation_score = 1.0 if has_official_gov else 0.0

    # 5. temporal_consistency_score (§53-F §2.5)
    temporal_claims = [c for c in claims if c.event_time_raw]
    if not temporal_claims:
        temporal_consistency_score = 0.5  # neutral when no temporal claims
    else:
        resolved_temporal = [c for c in temporal_claims if c.event_time is not None]
        temporal_consistency_score = len(resolved_temporal) / len(temporal_claims)

    # Weighted confidence score calculation
    raw_score = (
        cfg.weights.source_quality * source_quality_score
        + cfg.weights.corroboration * corroboration_score
        + cfg.weights.claim_consistency * claim_consistency_score
        + cfg.weights.official_confirmation * official_confirmation_score
        + cfg.weights.temporal_consistency * temporal_consistency_score
    )
    confidence_score = round(min(1.0, max(0.0, raw_score)), 4)

    # Derive confidence bucket (§53-F §5)
    if confidence_score >= cfg.thresholds.high:
        bucket = ConfidenceBucket.HIGH
    elif confidence_score >= cfg.thresholds.medium:
        bucket = ConfidenceBucket.MEDIUM
    else:
        bucket = ConfidenceBucket.LOW

    # Derive evidence_status (§53-F §4)
    has_retraction = is_retracted or any(
        "meralat" in c.claim_text.lower()
        or "retraksi" in c.claim_text.lower()
        or "kekeliruan" in c.claim_text.lower()
        for c in claims
    )
    if has_retraction:
        status = EvidenceStatus.RETRACTED
    elif unresolved_conflicts:
        status = EvidenceStatus.CONFLICTING
    elif len(claims) < 2:
        status = EvidenceStatus.INSUFFICIENT
    else:
        status = EvidenceStatus.SUPPORTED

    # Derive verification_level (§53-F §4)
    if has_official_gov:
        v_level = VerificationLevel.OFFICIAL_PRIMARY
    elif len(unique_families) >= 2:
        v_level = VerificationLevel.INDEPENDENTLY_CORROBORATED
    else:
        v_level = VerificationLevel.SINGLE_SOURCE

    return ConfidenceResult(
        confidence_score=confidence_score,
        confidence_bucket=bucket,
        evidence_status=status,
        verification_level=v_level,
        components={
            "source_quality": round(source_quality_score, 4),
            "corroboration": round(corroboration_score, 4),
            "claim_consistency": round(claim_consistency_score, 4),
            "official_confirmation": round(official_confirmation_score, 4),
            "temporal_consistency": round(temporal_consistency_score, 4),
        },
    )
