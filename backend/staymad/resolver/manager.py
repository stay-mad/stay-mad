"""Event Clustering Manager orchestrating the 3-Tier Hybrid Resolution Pipeline.

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D), ADR-005, Addendum §6
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.staymad.db.models.article import ArticleVersion
from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.enums import (
    EventCategory,
    EventClaimRole,
    EventRelationType,
    ResolutionDecision,
)
from backend.staymad.db.models.event import Event, EventClaim
from backend.staymad.db.models.location import Location
from backend.staymad.db.models.relation import EventRelation
from backend.staymad.llm.base import BaseGeminiClient
from backend.staymad.llm.factory import get_llm_client
from backend.staymad.llm.schemas import AdjudicateDecision
from backend.staymad.resolver.audit import create_and_persist_membership_audit
from backend.staymad.resolver.config import ResolverConfig
from backend.staymad.resolver.tier1_deterministic import (
    ArticleCandidate,
    EventAnchor,
    check_hard_constraints,
    extract_indonesian_region,
)
from backend.staymad.resolver.tier2_embedding import (
    BaseEmbeddingGenerator,
    compute_composite_score,
    evaluate_tier2_threshold,
    get_embedding_generator,
)
from backend.staymad.resolver.tier3_adjudicate import adjudicate_candidates

logger = logging.getLogger(__name__)

AblationMode = Literal["tier1", "tier2", "tier3"]


@dataclass
class ResolutionResult:
    """Outcome of resolving an article against event clusters."""

    article_version_id: uuid.UUID
    decision: ResolutionDecision
    event_id: uuid.UUID
    tier_used: str
    deterministic_signals: dict[str, Any]
    decision_reason_codes: list[str]
    confidence: float
    is_new_event: bool = False


class EventResolverManager:
    """3-Tier Hybrid Event Resolver with Ablation support and audit logging."""

    def __init__(
        self,
        session: Session,
        config: ResolverConfig | None = None,
        llm_client: BaseGeminiClient | None = None,
        embedding_generator: BaseEmbeddingGenerator | None = None,
        ablation_mode: AblationMode = "tier3",
    ) -> None:
        self.session = session
        self.config = config or ResolverConfig.load()
        self.llm_client = llm_client or get_llm_client(use_mock=True)
        self.embedding_generator = embedding_generator or get_embedding_generator(
            use_mock=True
        )
        self.ablation_mode = ablation_mode
        self.anchors: list[EventAnchor] = []
        self._load_active_anchors_from_db()

    def _load_active_anchors_from_db(self) -> None:
        """Load existing events from DB and initialize anchors."""
        stmt = select(Event)
        events = self.session.scalars(stmt).all()
        for evt in events:
            # Load claims for this event
            claim_texts = [
                ec.claim.claim_text
                for ec in evt.event_claims
                if ec.claim and ec.claim.claim_text
            ]
            source_families = {
                ec.claim.source.source_family
                for ec in evt.event_claims
                if ec.claim and ec.claim.source and ec.claim.source.source_family
            }
            art_ids = [
                str(ec.claim.article_version_id) for ec in evt.event_claims if ec.claim
            ]

            prov, city = None, None
            if evt.primary_location:
                prov = evt.primary_location.province
                city = evt.primary_location.city

            headline = evt.event_type
            if evt.snapshots:
                latest = evt.snapshots[-1]
                headline = latest.headline

            summary_text = f"{headline} {' '.join(claim_texts[:3])}"
            emb = self.embedding_generator.embed_text(summary_text)

            center = evt.time_window_start
            if evt.time_window_start and evt.time_window_end:
                mid_ts = (
                    evt.time_window_start.timestamp() + evt.time_window_end.timestamp()
                ) / 2
                center = datetime.fromtimestamp(mid_ts, tz=evt.time_window_start.tzinfo)

            anchor = EventAnchor(
                event_id=str(evt.id),
                event_type=evt.event_type,
                category=evt.category.value.lower(),
                headline=headline,
                time_window_start=evt.time_window_start,
                time_window_end=evt.time_window_end,
                time_window_center=center,
                primary_location_name=evt.primary_location.canonical_name
                if evt.primary_location
                else None,
                province=prov,
                city=city,
                representative_claims=claim_texts[:5],
                source_families=source_families,
                embedding=emb,
                article_version_ids=art_ids,
            )
            self.anchors.append(anchor)

    def _category_to_enum(self, cat_str: str) -> EventCategory:
        """Map category string to EventCategory enum."""
        norm = cat_str.upper().strip()
        for member in EventCategory:
            if member.name == norm or member.value == norm:
                return member
        return EventCategory.GOVERNMENT_AND_PUBLIC_POLICY

    def resolve_article(
        self,
        candidate: ArticleCandidate,
        processing_run_id: uuid.UUID,
        evidence_claim_ids: list[uuid.UUID] | None = None,
    ) -> ResolutionResult:
        """Resolve a single article candidate through the 3-Tier hybrid pipeline.

        Tier 1: Deterministic matching & hard constraints
        Tier 2: Embedding retrieval & composite scoring
        Tier 3: Gemini adjudication for ambiguous candidates (if ablation_mode == 'tier3')
        """
        claim_ids = [str(cid) for cid in (evidence_claim_ids or [])]
        art_ver_uuid = uuid.UUID(str(candidate.article_version_id))

        # Ensure candidate embedding is generated
        if not candidate.embedding:
            text_to_embed = f"{candidate.title} {' '.join(candidate.claims_text[:3])}"
            candidate.embedding = self.embedding_generator.embed_text(text_to_embed)

        # ----------------------------------------------------
        # TIER 1: Hard Constraints Filtering
        # ----------------------------------------------------
        passing_anchors: list[EventAnchor] = []
        tier1_failed_reasons: list[str] = []

        for anchor in self.anchors:
            passed, reason = check_hard_constraints(candidate, anchor, self.config)
            if passed:
                passing_anchors.append(anchor)
            elif reason:
                tier1_failed_reasons.append(reason)

        # If no anchor passes hard constraints -> SEPARATE_EVENT directly (no LLM needed)
        if not passing_anchors:
            tier_used = "TIER_1"
            reason_codes = (
                list(set(tier1_failed_reasons))
                if tier1_failed_reasons
                else ["NEW_EVENT"]
            )
            new_event = self._create_new_event(candidate, claim_ids, processing_run_id)

            signals = {
                "location_match": False,
                "category_match": True,
                "hard_constraints_failed": reason_codes,
                "tier_used": tier_used,
            }

            create_and_persist_membership_audit(
                session=self.session,
                article_version_id=art_ver_uuid,
                candidate_event_ids=[a.event_id for a in self.anchors],
                decision=ResolutionDecision.SEPARATE_EVENT,
                deterministic_signals=signals,
                decision_reason_codes=reason_codes,
                evidence_claim_ids=claim_ids,
                model_version=self.llm_client.model_version,
                prompt_version=self.llm_client.prompt_version,
                schema_version=self.llm_client.schema_version,
                processing_run_id=processing_run_id,
                tier_used=tier_used,
            )

            return ResolutionResult(
                article_version_id=art_ver_uuid,
                decision=ResolutionDecision.SEPARATE_EVENT,
                event_id=new_event.id,
                tier_used=tier_used,
                deterministic_signals=signals,
                decision_reason_codes=reason_codes,
                confidence=1.0,
                is_new_event=True,
            )

        # ----------------------------------------------------
        # ABLATION MODE 1: Only Deterministic (tier1)
        # ----------------------------------------------------
        if self.ablation_mode == "tier1":
            # In tier1 mode, if hard constraints pass and location/time match strongly, merge; else separate.
            best_anchor = passing_anchors[0]
            tier_used = "TIER_1"
            cand_prov, cand_city = candidate.province, candidate.city
            if not cand_prov:
                cand_prov, cand_city = extract_indonesian_region(candidate.location_raw)

            # Check if location matches best anchor
            loc_matched = bool(
                cand_city
                and best_anchor.city
                and cand_city.lower() == best_anchor.city.lower()
            )

            if loc_matched:
                decision = ResolutionDecision.SAME_EVENT
                reason_codes = ["LOC_MATCH", "TIME_WITHIN_WINDOW"]
                if candidate.source_family in best_anchor.source_families:
                    reason_codes.append("SOURCE_SYNDICATE")
                else:
                    reason_codes.append("CORROBORATED")
                self._merge_into_event(best_anchor, candidate, claim_ids)
                evt_id = uuid.UUID(best_anchor.event_id)
                is_new = False
            else:
                decision = ResolutionDecision.SEPARATE_EVENT
                reason_codes = ["LOC_INCOMPATIBLE"]
                new_evt = self._create_new_event(
                    candidate, claim_ids, processing_run_id
                )
                evt_id = new_evt.id
                is_new = True

            signals = {
                "location_match": loc_matched,
                "tier_used": tier_used,
                "ablation_mode": "tier1",
            }

            create_and_persist_membership_audit(
                session=self.session,
                article_version_id=art_ver_uuid,
                candidate_event_ids=[a.event_id for a in passing_anchors],
                decision=decision,
                deterministic_signals=signals,
                decision_reason_codes=reason_codes,
                evidence_claim_ids=claim_ids,
                model_version=self.llm_client.model_version,
                prompt_version=self.llm_client.prompt_version,
                schema_version=self.llm_client.schema_version,
                processing_run_id=processing_run_id,
                tier_used=tier_used,
            )

            return ResolutionResult(
                article_version_id=art_ver_uuid,
                decision=decision,
                event_id=evt_id,
                tier_used=tier_used,
                deterministic_signals=signals,
                decision_reason_codes=reason_codes,
                confidence=0.85,
                is_new_event=is_new,
            )

        # ----------------------------------------------------
        # TIER 2: Embedding Retrieval & Composite Scoring
        # ----------------------------------------------------
        scored_anchors: list[tuple[EventAnchor, float, dict[str, Any]]] = []
        for anchor in passing_anchors:
            score, sigs = compute_composite_score(candidate, anchor, self.config)
            scored_anchors.append((anchor, score, sigs))

        # Sort descending by composite score
        scored_anchors.sort(key=lambda x: x[1], reverse=True)
        best_anchor, best_score, best_signals = scored_anchors[0]
        threshold_eval = evaluate_tier2_threshold(best_score, self.config)

        # ----------------------------------------------------
        # ABLATION MODE 2: Tier 1 + Tier 2 Embedding only
        # ----------------------------------------------------
        if self.ablation_mode == "tier2":
            tier_used = "TIER_2"
            if threshold_eval == "SAME_EVENT" or (
                threshold_eval == "AMBIGUOUS" and best_score >= 0.55
            ):
                decision = ResolutionDecision.SAME_EVENT
                reason_codes = ["LOC_MATCH", "TIME_WITHIN_WINDOW"]
                if candidate.source_family in best_anchor.source_families:
                    reason_codes.append("SOURCE_SYNDICATE")
                else:
                    reason_codes.append("CORROBORATED")
                self._merge_into_event(best_anchor, candidate, claim_ids)
                evt_id = uuid.UUID(best_anchor.event_id)
                is_new = False
            else:
                # Ambiguous or separate -> fallback to separate
                decision = ResolutionDecision.SEPARATE_EVENT
                reason_codes = (
                    ["BELOW_THRESHOLD"]
                    if threshold_eval == "SEPARATE_EVENT"
                    else ["AMBIGUOUS"]
                )
                new_evt = self._create_new_event(
                    candidate, claim_ids, processing_run_id
                )
                evt_id = new_evt.id
                is_new = True

            signals = dict(best_signals)
            signals["ablation_mode"] = "tier2"

            create_and_persist_membership_audit(
                session=self.session,
                article_version_id=art_ver_uuid,
                candidate_event_ids=[a[0].event_id for a in scored_anchors],
                decision=decision,
                deterministic_signals=signals,
                decision_reason_codes=reason_codes,
                evidence_claim_ids=claim_ids,
                model_version=self.llm_client.model_version,
                prompt_version=self.llm_client.prompt_version,
                schema_version=self.llm_client.schema_version,
                processing_run_id=processing_run_id,
                tier_used=tier_used,
            )

            return ResolutionResult(
                article_version_id=art_ver_uuid,
                decision=decision,
                event_id=evt_id,
                tier_used=tier_used,
                deterministic_signals=signals,
                decision_reason_codes=reason_codes,
                confidence=best_score,
                is_new_event=is_new,
            )

        # ----------------------------------------------------
        # FULL HYBRID MODE (tier3): Tier 1 + Tier 2 + Tier 3 Adjudicate
        # ----------------------------------------------------
        if threshold_eval == "SAME_EVENT":
            # Confident merge from Tier 2 without calling Gemini
            tier_used = "TIER_2"
            decision = ResolutionDecision.SAME_EVENT
            reason_codes = ["LOC_MATCH", "TIME_WITHIN_WINDOW"]
            if candidate.source_family in best_anchor.source_families:
                reason_codes.append("SOURCE_SYNDICATE")
            else:
                reason_codes.append("CORROBORATED")

            self._merge_into_event(best_anchor, candidate, claim_ids)
            evt_id = uuid.UUID(best_anchor.event_id)
            is_new = False
            conf = min(0.99, max(0.75, best_score))

        elif threshold_eval == "SEPARATE_EVENT":
            # Confident separation from Tier 2 without calling Gemini
            tier_used = "TIER_2"
            decision = ResolutionDecision.SEPARATE_EVENT
            reason_codes = (
                ["LOC_INCOMPATIBLE", "TIME_INCOMPATIBLE"]
                if best_score < 0.20
                else ["AMBIGUOUS"]
            )
            new_evt = self._create_new_event(candidate, claim_ids, processing_run_id)
            evt_id = new_evt.id
            is_new = True
            conf = 0.90

        else:
            # Ambiguous: Call Tier 3 Gemini Call 2 Adjudicate
            tier_used = "TIER_3"
            adjudicate_results = adjudicate_candidates(
                anchor=best_anchor,
                candidate_tuples=[(candidate, best_score, best_signals)],
                llm_client=self.llm_client,
                config=self.config,
                processing_run_id=str(processing_run_id),
            )

            if not adjudicate_results:
                adj_decision = AdjudicateDecision(
                    article_version_id=str(candidate.article_version_id),
                    decision="SEPARATE_EVENT",
                    decision_reason_codes=["ADJUDICATION_FAILED"],
                    confidence=0.0,
                    notes="Empty adjudication decisions list",
                )
            else:
                adj_decision = adjudicate_results[0]
            dec_str = adj_decision.decision
            reason_codes = adj_decision.decision_reason_codes
            conf = adj_decision.confidence

            if dec_str == "SAME_EVENT":
                decision = ResolutionDecision.SAME_EVENT
                self._merge_into_event(best_anchor, candidate, claim_ids)
                evt_id = uuid.UUID(best_anchor.event_id)
                is_new = False
            elif dec_str == "RELATED_EVENT":
                decision = ResolutionDecision.RELATED_EVENT
                new_evt = self._create_new_event(
                    candidate, claim_ids, processing_run_id
                )
                evt_id = new_evt.id
                is_new = True
                # Link via EventRelation
                rel = EventRelation(
                    id=uuid.uuid4(),
                    from_event_id=new_evt.id,
                    to_event_id=uuid.UUID(best_anchor.event_id),
                    relation_type=EventRelationType.RELATED_TO,
                    confidence=conf,
                    processing_run_id=processing_run_id,
                )
                self.session.add(rel)
            elif dec_str == "NEEDS_REVIEW":
                decision = ResolutionDecision.NEEDS_REVIEW
                new_evt = self._create_new_event(
                    candidate, claim_ids, processing_run_id
                )
                evt_id = new_evt.id
                is_new = True
            else:
                decision = ResolutionDecision.SEPARATE_EVENT
                new_evt = self._create_new_event(
                    candidate, claim_ids, processing_run_id
                )
                evt_id = new_evt.id
                is_new = True

        signals = dict(best_signals)
        signals["tier_used"] = tier_used

        create_and_persist_membership_audit(
            session=self.session,
            article_version_id=art_ver_uuid,
            candidate_event_ids=[a[0].event_id for a in scored_anchors],
            decision=decision,
            deterministic_signals=signals,
            decision_reason_codes=reason_codes,
            evidence_claim_ids=claim_ids,
            model_version=self.llm_client.model_version,
            prompt_version=self.llm_client.prompt_version,
            schema_version=self.llm_client.schema_version,
            processing_run_id=processing_run_id,
            tier_used=tier_used,
        )

        return ResolutionResult(
            article_version_id=art_ver_uuid,
            decision=decision,
            event_id=evt_id,
            tier_used=tier_used,
            deterministic_signals=signals,
            decision_reason_codes=reason_codes,
            confidence=conf,
            is_new_event=is_new,
        )

    def _create_new_event(
        self,
        candidate: ArticleCandidate,
        claim_ids: list[str],
        processing_run_id: uuid.UUID,
    ) -> Event:
        """Create a new Event entity and associate candidate claims with role PRIMARY."""
        cat_enum = self._category_to_enum(candidate.category)

        # Primary location lookup or creation
        loc_id = None
        cand_prov, cand_city = candidate.province, candidate.city
        if not cand_prov:
            cand_prov, cand_city = extract_indonesian_region(candidate.location_raw)

        if cand_city or cand_prov:
            canonical_name = cand_city or cand_prov or "Indonesia"
            stmt = select(Location).where(Location.canonical_name == canonical_name)
            loc = self.session.scalars(stmt).first()
            if not loc:
                from backend.staymad.db.models.enums import GeoLevel

                loc = Location(
                    id=uuid.uuid4(),
                    canonical_name=canonical_name,
                    source_text=candidate.location_raw or canonical_name,
                    city=cand_city,
                    province=cand_prov,
                    country="Indonesia",
                    geo_level=GeoLevel.CITY if cand_city else GeoLevel.PROVINCE,
                )
                self.session.add(loc)
                self.session.flush()
            loc_id = loc.id

        start_time = candidate.event_time or candidate.published_time
        new_event = Event(
            id=uuid.uuid4(),
            event_type=candidate.title[:100] or "Peristiwa Baru",
            category=cat_enum,
            primary_location_id=loc_id,
            time_window_start=start_time,
            time_window_end=start_time,
        )
        self.session.add(new_event)
        self.session.flush()

        # Link claims
        for cid in claim_ids:
            ec = EventClaim(
                id=uuid.uuid4(),
                event_id=new_event.id,
                claim_id=uuid.UUID(cid),
                role=EventClaimRole.PRIMARY,
            )
            self.session.add(ec)

        # Register as a new anchor
        new_anchor = EventAnchor(
            event_id=str(new_event.id),
            event_type=new_event.event_type,
            category=candidate.category.lower(),
            headline=candidate.title,
            time_window_start=start_time,
            time_window_end=start_time,
            time_window_center=start_time,
            primary_location_name=cand_city or cand_prov,
            province=cand_prov,
            city=cand_city,
            representative_claims=candidate.claims_text[:3],
            source_families={candidate.source_family},
            embedding=candidate.embedding,
            article_version_ids=[str(candidate.article_version_id)],
        )
        self.anchors.append(new_anchor)
        return new_event

    def _merge_into_event(
        self,
        anchor: EventAnchor,
        candidate: ArticleCandidate,
        claim_ids: list[str],
    ) -> None:
        """Merge candidate claims into existing event with role SUPPORTING and update anchor."""
        event_uuid = uuid.UUID(anchor.event_id)
        for cid in claim_ids:
            ec = EventClaim(
                id=uuid.uuid4(),
                event_id=event_uuid,
                claim_id=uuid.UUID(cid),
                role=EventClaimRole.SUPPORTING,
            )
            self.session.add(ec)

        # Update event time window in DB
        evt = self.session.get(Event, event_uuid)
        cand_time = candidate.event_time or candidate.published_time
        if evt and cand_time:
            t_start = evt.time_window_start
            if t_start is not None and t_start.tzinfo != cand_time.tzinfo:
                t_start = t_start.replace(tzinfo=cand_time.tzinfo)
            if evt.time_window_start is None or cand_time < t_start:
                evt.time_window_start = cand_time

            t_end = evt.time_window_end
            if t_end is not None and t_end.tzinfo != cand_time.tzinfo:
                t_end = t_end.replace(tzinfo=cand_time.tzinfo)
            if evt.time_window_end is None or cand_time > t_end:
                evt.time_window_end = cand_time

        # Update in-memory anchor
        anchor.source_families.add(candidate.source_family)
        anchor.article_version_ids.append(str(candidate.article_version_id))
        if candidate.claims_text:
            anchor.representative_claims.extend(candidate.claims_text[:2])
            anchor.representative_claims = anchor.representative_claims[:5]

    def resolve_article_version(
        self,
        article_version: ArticleVersion,
        claims: list[Claim],
        processing_run_id: uuid.UUID,
    ) -> ResolutionResult:
        """Helper to resolve a database ArticleVersion entity and its extracted claims."""
        cat_str = (
            article_version.article.category
            if article_version.article
            else "disaster_and_weather"
        )
        src_family = (
            article_version.article.source.source_family
            if article_version.article and article_version.article.source
            else "UNKNOWN"
        )
        src_tier = (
            article_version.article.source.source_tier.value
            if article_version.article and article_version.article.source
            else "TIER_2"
        )

        first_claim_loc = claims[0].location_raw if claims else None
        first_claim_time = (
            claims[0].event_time if claims else article_version.published_time
        )
        prov, city = extract_indonesian_region(
            first_claim_loc or f"{article_version.title} {article_version.excerpt}"
        )

        candidate = ArticleCandidate(
            article_version_id=str(article_version.id),
            article_id=str(article_version.article_id),
            title=article_version.title,
            excerpt=article_version.excerpt,
            category=cat_str,
            event_time=first_claim_time,
            published_time=article_version.published_time,
            location_raw=first_claim_loc,
            province=prov,
            city=city,
            entities=[],
            source_family=src_family,
            source_tier=src_tier,
            content_hash=article_version.content_hash,
            claims_text=[c.claim_text for c in claims],
        )

        return self.resolve_article(
            candidate=candidate,
            processing_run_id=processing_run_id,
            evidence_claim_ids=[c.id for c in claims],
        )
