"""Actionability gating rules and safety policy enforcement.

Authority: docs/architecture/H-actionability-algorithm.md §53-H, ADR-006, Addendum §5.6 & §8
"""

from __future__ import annotations

from typing import Any

from backend.staymad.db.models.enums import ActionabilityLevel, ActionSourceType

AUTHORIZED_EMERGENCY_FAMILIES = {
    "GOV_BMKG",  # BMKG (cuaca, gempa, tsunami)
    "GOV_BPBD_DKI",  # BPBD DKI Jakarta (banjir, darurat daerah)
    "GOV_BNPB",  # BNPB Indonesia (bencana nasional)
    "GOV_SETKAB",  # Sekretariat Kabinet (kebijakan darurat presiden)
}


class ActionSafetyViolation(ValueError):
    """Raised when an action proposal violates safety policies."""


class ActionValidationResult:
    """Audit result for an action proposition."""

    def __init__(
        self,
        is_allowed: bool,
        final_level: ActionabilityLevel,
        source_type: ActionSourceType,
        reason: str,
        violation_detected: bool = False,
    ) -> None:
        self.is_allowed = is_allowed
        self.final_level = final_level
        self.source_type = source_type
        self.reason = reason
        self.violation_detected = violation_detected


def is_official_emergency_source(source_family: str, source_tier: str | int) -> bool:
    """Gate 1: Source Authorization.

    ACTION_REQUIRED and ACTION_RECOMMENDED may ONLY originate from authorized emergency agencies.
    Authority: §53-H §3 Gate 1 & ADR-006 Opsi A.
    """
    tier_str = str(source_tier).upper()
    is_tier_1 = tier_str in ("TIER_1", "1")
    return source_family in AUTHORIZED_EMERGENCY_FAMILIES and is_tier_1


def validate_action_gate(
    action_level: ActionabilityLevel | str,
    action_text: str,
    source_family: str,
    source_tier: str | int,
    evidence_claim_ids: list[Any],
    has_official_attribution: bool = False,
) -> ActionValidationResult:
    """Enforce strict safety gates on suggested actions.

    Ensures unsupported_action_rate == 0.00.
    """
    if isinstance(action_level, ActionabilityLevel):
        level_norm = action_level
    else:
        val_str = str(action_level).split(".")[-1].strip().upper()
        level_norm = ActionabilityLevel(val_str)

    # Low risk actions: OPTIONAL, INFORMATIONAL, NO_IMMEDIATE_ACTION
    if level_norm in (
        ActionabilityLevel.OPTIONAL,
        ActionabilityLevel.INFORMATIONAL,
        ActionabilityLevel.NO_IMMEDIATE_ACTION,
    ):
        return ActionValidationResult(
            is_allowed=True,
            final_level=level_norm,
            source_type=ActionSourceType.INFORMATIONAL,
            reason="Informational or optional action",
            violation_detected=False,
        )

    # High risk actions: ACTION_REQUIRED or ACTION_RECOMMENDED
    # 1. Gate 1: Check source authorization
    is_authorized = (
        is_official_emergency_source(source_family, source_tier)
        or has_official_attribution
    )

    if not is_authorized:
        # VIOLATION: Non-official source attempting to issue emergency actions
        # (e.g. prompt injection in art_demo_07 or unverified media rumors)
        return ActionValidationResult(
            is_allowed=False,
            final_level=ActionabilityLevel.NO_IMMEDIATE_ACTION,
            source_type=ActionSourceType.INFORMATIONAL,
            reason=(
                f"SAFETY POLICY VIOLATION (ADR-006): Action level '{level_norm.value}' "
                f"rejected because source_family '{source_family}' (tier {source_tier}) is not an authorized official emergency authority."
            ),
            violation_detected=True,
        )

    # 2. Gate 2: Claim Grounding
    if not evidence_claim_ids:
        return ActionValidationResult(
            is_allowed=False,
            final_level=ActionabilityLevel.NO_IMMEDIATE_ACTION,
            source_type=ActionSourceType.INFORMATIONAL,
            reason="Ungrounded action: evidence_claim_ids must not be empty.",
            violation_detected=True,
        )

    return ActionValidationResult(
        is_allowed=True,
        final_level=level_norm,
        source_type=ActionSourceType.OFFICIAL_EMERGENCY,
        reason="Approved official emergency action",
        violation_detected=False,
    )
