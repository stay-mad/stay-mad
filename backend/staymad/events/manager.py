"""Event synthesis and snapshot orchestrator.

Authority: docs/architecture/B-data-model.md, docs/architecture/E-timeline-algorithm.md,
docs/architecture/F-confidence-algorithm.md, docs/architecture/G-importance-algorithm.md
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.staymad.actions.gating import validate_action_gate
from backend.staymad.confidence.calculator import calculate_confidence
from backend.staymad.db.models.enums import (
    ActionabilityLevel,
    DataMode,
)
from backend.staymad.db.models.event import Event, EventSnapshot
from backend.staymad.events.changes import detect_changeset
from backend.staymad.events.conflicts import ConflictDetector
from backend.staymad.intelligence.calculator import calculate_importance
from backend.staymad.llm.base import (
    PROMPT_VERSION_SYNTHESIZE,
    SCHEMA_VERSION_SYNTHESIZE,
    BaseGeminiClient,
)
from backend.staymad.llm.factory import get_llm_client
from backend.staymad.llm.schemas import (
    SynthesizeClaimInput,
    SynthesizeConflictInput,
    SynthesizeInput,
    SynthesizeLocationInput,
)
from backend.staymad.timeline.builder import build_timeline_entries

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim


class EventSynthesisManager:
    """Coordinates conflict detection, scoring, synthesis, and snapshot publishing."""

    def __init__(
        self,
        session: Session,
        llm_client: BaseGeminiClient | None = None,
    ) -> None:
        self.session = session
        self.llm_client = llm_client or get_llm_client(use_mock=True)

    def synthesize_event_snapshot(
        self,
        event_id: uuid.UUID,
        processing_run_id: uuid.UUID,
        newly_added_claims: list[Claim] | None = None,
        force_snapshot: bool = False,
    ) -> EventSnapshot | None:
        """Synthesize and publish an immutable EventSnapshot with timeline, conflicts, and changeset."""
        event = self.session.get(Event, event_id)
        if not event:
            return None

        # Gather all claims associated with this event
        all_claims = [ec.claim for ec in event.event_claims if ec.claim is not None]
        if not all_claims:
            return None

        # 1. Fetch or initialize previous snapshot
        prev_snapshot = event.snapshots[-1] if event.snapshots else None
        prev_version = prev_snapshot.version_number if prev_snapshot else 0

        # Temporary snapshot id for joining children
        snapshot_id = uuid.uuid4()

        # 2. Conflict Detection & Resolution
        existing_conflicts = list(event.conflicts)
        detected_conflicts = ConflictDetector.detect_conflicts(
            all_claims, event_id=event.id, snapshot_id=snapshot_id
        )

        # Merge conflicts without duplicating
        combined_conflicts = list(existing_conflicts)
        existing_pairs = {
            tuple(sorted([str(cf.claim_a_id), str(cf.claim_b_id)]))
            for cf in existing_conflicts
        }
        for dcf in detected_conflicts:
            d_pair = tuple(sorted([str(dcf.claim_a_id), str(dcf.claim_b_id)]))
            if d_pair not in existing_pairs:
                combined_conflicts.append(dcf)
                existing_pairs.add(d_pair)

        # Resolve conflicts with updates if applicable
        resolved_conflicts = ConflictDetector.resolve_conflicts_with_update(
            combined_conflicts, all_claims
        )
        for cf in resolved_conflicts:
            if cf not in event.conflicts:
                self.session.add(cf)

        # 3. Calculate Confidence Score & Derived Enums (§53-F)
        conf_res = calculate_confidence(all_claims, conflicts=resolved_conflicts)

        # 4. Check Actionability Gate (§53-H, ADR-006)
        action_level = ActionabilityLevel.INFORMATIONAL
        for c in all_claims:
            fam = c.source.source_family if c.source else ""
            tier = (
                c.source.source_tier.value
                if (c.source and hasattr(c.source.source_tier, "value"))
                else "TIER_2"
            )
            lower_text = c.claim_text.lower()
            if any(
                w in lower_text
                for w in ("evakuasi", "posko pengungsian", "siaga 2", "diinstruksikan")
            ):
                gate_res = validate_action_gate(
                    action_level=ActionabilityLevel.ACTION_REQUIRED,
                    action_text=c.claim_text,
                    source_family=fam,
                    source_tier=tier,
                    evidence_claim_ids=[str(c.id)],
                )
                if gate_res.is_allowed:
                    action_level = ActionabilityLevel.ACTION_REQUIRED
                    break
            elif any(w in lower_text for w in ("imbau", "waspada", "antisipasi")):
                gate_res = validate_action_gate(
                    action_level=ActionabilityLevel.ACTION_RECOMMENDED,
                    action_text=c.claim_text,
                    source_family=fam,
                    source_tier=tier,
                    evidence_claim_ids=[str(c.id)],
                )
                if gate_res.is_allowed:
                    action_level = ActionabilityLevel.ACTION_RECOMMENDED

        # 5. Calculate Importance Score (§53-G)
        imp_res = calculate_importance(
            event=event,
            claims=all_claims,
            latest_update_time=datetime.now(UTC),
            snapshots_count_6h=len(event.snapshots) + 1,
            new_claims_count_6h=len(newly_added_claims or []),
            actionability_level=action_level,
        )

        # 6. Call Type 3: Synthesize (Gemini / Deterministic)
        loc_input = None
        if event.primary_location:
            loc_input = SynthesizeLocationInput(
                city=event.primary_location.city,
                province=event.primary_location.province,
                country=event.primary_location.country or "Indonesia",
            )

        synth_claims = [
            SynthesizeClaimInput(
                claim_id=str(c.id),
                claim_text=c.claim_text,
                source_span=c.source_span or "",
                source_tier=c.source.source_tier.value
                if (c.source and hasattr(c.source.source_tier, "value"))
                else "TIER_2",
                source_family=c.source.source_family if c.source else "UNKNOWN",
                event_time=c.event_time.isoformat() if c.event_time else None,
                event_time_qualifier=c.event_time_qualifier,
                extraction_confidence=c.extraction_confidence,
                role="PRIMARY" if i < 3 else "SUPPORTING",
            )
            for i, c in enumerate(all_claims)
        ]

        synth_conflicts = [
            SynthesizeConflictInput(
                field_name=cf.field_name,
                value_a=cf.value_a,
                value_b=cf.value_b,
                claim_a_id=str(cf.claim_a_id),
                claim_b_id=str(cf.claim_b_id),
            )
            for cf in resolved_conflicts
            if not cf.resolved
        ]

        synth_input = SynthesizeInput(
            schema_version=SCHEMA_VERSION_SYNTHESIZE,
            processing_run_id=str(processing_run_id),
            event_id=str(event.id),
            category=event.category.value
            if hasattr(event.category, "value")
            else str(event.category),
            primary_location=loc_input,
            time_window_start=event.time_window_start.isoformat()
            if event.time_window_start
            else None,
            time_window_end=event.time_window_end.isoformat()
            if event.time_window_end
            else None,
            output_language="id",
            claims=synth_claims,
            conflicts=synth_conflicts,
            previous_snapshot_id=str(prev_snapshot.id) if prev_snapshot else None,
        )

        synth_resp = self.llm_client.synthesize(synth_input)

        # 7. Material Change Detection (Negative Case check test_acc_05b)
        active_new_claims = newly_added_claims or []
        detected_changes = detect_changeset(
            prev_snapshot=prev_snapshot,
            new_snapshot=EventSnapshot(
                id=snapshot_id,
                event_id=event.id,
                version_number=prev_version + 1,
                headline=synth_resp.headline,
                what_happened=synth_resp.what_happened.text or "",
                what_happened_evidence_claim_ids=synth_resp.what_happened.evidence_claim_ids
                if synth_resp.what_happened
                else [],
                why_it_matters=synth_resp.why_it_matters.text
                if synth_resp.why_it_matters
                else None,
                why_it_matters_evidence_claim_ids=synth_resp.why_it_matters.evidence_claim_ids
                if synth_resp.why_it_matters
                else [],
                who_is_affected=synth_resp.who_is_affected.text
                if synth_resp.who_is_affected
                else None,
                who_is_affected_evidence_claim_ids=synth_resp.who_is_affected.evidence_claim_ids
                if synth_resp.who_is_affected
                else [],
                what_is_unknown=synth_resp.what_is_unknown.text
                if synth_resp.what_is_unknown
                else None,
                conflict_summary=synth_resp.conflict_summary.text
                if synth_resp.conflict_summary
                else None,
                conflict_summary_evidence_claim_ids=synth_resp.conflict_summary.evidence_claim_ids
                if synth_resp.conflict_summary
                else [],
                confidence_score=conf_res.confidence_score,
                confidence_bucket=conf_res.confidence_bucket,
                evidence_status=conf_res.evidence_status,
                verification_level=conf_res.verification_level,
                actionability_level=action_level,
                importance_score=imp_res.importance_score,
                urgency_score=imp_res.urgency_score,
                model_version=self.llm_client.model_version,
                prompt_version=PROMPT_VERSION_SYNTHESIZE,
                schema_version=SCHEMA_VERSION_SYNTHESIZE,
                processing_run_id=processing_run_id,
            ),
            new_claims=active_new_claims,
            resolved_conflicts=[cf for cf in resolved_conflicts if cf.resolved],
        )

        # If previous snapshot exists and no material changes detected (wording-only reprocessing),
        # suppress creating redundant snapshot unless force_snapshot=True
        if prev_snapshot and not detected_changes and not force_snapshot:
            # Wording-only / non-material reprocessing
            return prev_snapshot

        # 8. Create and Persist Immutable EventSnapshot
        new_snapshot = EventSnapshot(
            id=snapshot_id,
            event_id=event.id,
            version_number=prev_version + 1,
            published_at=datetime.now(UTC),
            headline=synth_resp.headline,
            what_happened=synth_resp.what_happened.text or "",
            what_happened_evidence_claim_ids=synth_resp.what_happened.evidence_claim_ids
            if synth_resp.what_happened
            else [],
            why_it_matters=synth_resp.why_it_matters.text
            if synth_resp.why_it_matters
            else None,
            why_it_matters_evidence_claim_ids=synth_resp.why_it_matters.evidence_claim_ids
            if synth_resp.why_it_matters
            else [],
            who_is_affected=synth_resp.who_is_affected.text
            if synth_resp.who_is_affected
            else None,
            who_is_affected_evidence_claim_ids=synth_resp.who_is_affected.evidence_claim_ids
            if synth_resp.who_is_affected
            else [],
            what_is_unknown=synth_resp.what_is_unknown.text
            if synth_resp.what_is_unknown
            else None,
            conflict_summary=synth_resp.conflict_summary.text
            if synth_resp.conflict_summary
            else None,
            conflict_summary_evidence_claim_ids=synth_resp.conflict_summary.evidence_claim_ids
            if synth_resp.conflict_summary
            else [],
            confidence_score=conf_res.confidence_score,
            confidence_bucket=conf_res.confidence_bucket,
            evidence_status=conf_res.evidence_status,
            verification_level=conf_res.verification_level,
            actionability_level=action_level,
            importance_score=imp_res.importance_score,
            urgency_score=imp_res.urgency_score,
            data_mode=(
                DataMode[os.getenv("DATA_MODE", "live").upper()]
                if os.getenv("DATA_MODE", "live").upper() in DataMode.__members__
                else DataMode.LIVE
            ),
            last_processed_at=datetime.now(UTC),
            model_version=self.llm_client.model_version,
            prompt_version=PROMPT_VERSION_SYNTHESIZE,
            schema_version=SCHEMA_VERSION_SYNTHESIZE,
            processing_run_id=processing_run_id,
        )
        self.session.add(new_snapshot)

        # 9. Build and Persist Timeline Entries
        timeline_entries = build_timeline_entries(
            claims=all_claims,
            event_id=event.id,
            snapshot_id=snapshot_id,
        )
        for te in timeline_entries:
            self.session.add(te)

        # 10. Persist EventChanges
        for chg in detected_changes:
            self.session.add(chg)

        self.session.commit()
        return new_snapshot
