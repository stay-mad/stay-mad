"""Tier 3: Gemini Adjudication wrapper, chunking, and transitive cluster guard.

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D), docs/architecture/C-gemini-architecture.md (§53-C)
"""

from __future__ import annotations

import logging
from typing import Any

from backend.staymad.llm.base import BaseGeminiClient
from backend.staymad.llm.schemas import (
    AdjudicateDecision,
    AdjudicateInput,
    AnchorSummary,
    CandidateArticleInput,
)
from backend.staymad.resolver.config import ResolverConfig
from backend.staymad.resolver.tier1_deterministic import ArticleCandidate, EventAnchor

logger = logging.getLogger(__name__)


def build_candidate_article_input(
    candidate: ArticleCandidate,
    deterministic_score: float,
    deterministic_signals: dict[str, Any],
) -> CandidateArticleInput:
    """Format an article candidate into CandidateArticleInput for Gemini Call Type 2."""
    top_claims = (
        candidate.claims_text[:3] if candidate.claims_text else [candidate.title]
    )
    loc = candidate.city or candidate.province or candidate.location_raw
    pub_iso = candidate.published_time.isoformat() if candidate.published_time else None
    evt_iso = candidate.event_time.isoformat() if candidate.event_time else None

    return CandidateArticleInput(
        article_version_id=str(candidate.article_version_id),
        source_tier=candidate.source_tier,
        source_family=candidate.source_family,
        title=candidate.title,
        excerpt=candidate.excerpt[:500],
        published_time=pub_iso,
        primary_location_raw=loc,
        primary_event_time_raw=evt_iso,
        deterministic_score=deterministic_score,
        deterministic_signals=deterministic_signals,
        top_claims=top_claims,
    )


def adjudicate_candidates(
    anchor: EventAnchor,
    candidate_tuples: list[tuple[ArticleCandidate, float, dict[str, Any]]],
    llm_client: BaseGeminiClient,
    config: ResolverConfig,
    processing_run_id: str,
) -> list[AdjudicateDecision]:
    """Execute Tier 3 Gemini adjudication for ambiguous candidates.

    Guarantees:
    1. Transitive Cluster Guard: Each candidate article is verified independently against
       canonical anchor evidence, not linked transitively to other candidate articles (§53-D 4.1).
    2. Candidate Chunking: Batched by max_candidates_per_call (default: 5) to respect token limits.
    3. Safety Override: If decision == SAME_EVENT but confidence < cutoff (0.60),
       overridden to NEEDS_REVIEW (§53-C Call Type 2).
    """
    if not candidate_tuples:
        return []

    anchor_summary = AnchorSummary(
        headline=anchor.headline,
        category=anchor.category,
        primary_location=anchor.primary_location_name,
        time_window_start=anchor.time_window_start.isoformat()
        if anchor.time_window_start
        else None,
        time_window_end=anchor.time_window_end.isoformat()
        if anchor.time_window_end
        else None,
        representative_claims=anchor.representative_claims[:5],
    )

    max_batch = config.adjudication.max_candidates_per_call
    all_decisions: list[AdjudicateDecision] = []

    for i in range(0, len(candidate_tuples), max_batch):
        batch = candidate_tuples[i : i + max_batch]
        candidate_inputs = [
            build_candidate_article_input(cand, score, signals)
            for cand, score, signals in batch
        ]

        payload = AdjudicateInput(
            schema_version="1.0",
            processing_run_id=processing_run_id,
            anchor_event_id=str(anchor.event_id),
            anchor_summary=anchor_summary,
            candidate_articles=candidate_inputs,
        )

        try:
            response = llm_client.adjudicate(payload)
            batch_decisions = response.decisions
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"Adjudication call failed: {e}; falling back to SEPARATE_EVENT"
            )
            batch_decisions = [
                AdjudicateDecision(
                    article_version_id=str(cand.article_version_id),
                    decision="SEPARATE_EVENT",
                    decision_reason_codes=["ADJUDICATION_FAILED"],
                    confidence=0.0,
                    notes=f"Adjudication error: {e}",
                )
                for cand, _, _ in batch
            ]

        # Enforce override rule post-check and guarantee every candidate has a decision
        decisions_by_id = {d.article_version_id: d for d in batch_decisions}
        normalized_batch_decisions: list[AdjudicateDecision] = []
        for cand, _, _ in batch:
            cand_id_str = str(cand.article_version_id)
            if cand_id_str in decisions_by_id:
                d = decisions_by_id[cand_id_str]
            elif batch_decisions and len(batch) == 1:
                d = batch_decisions[0]
                d.article_version_id = cand_id_str
            else:
                d = AdjudicateDecision(
                    article_version_id=cand_id_str,
                    decision="SEPARATE_EVENT",
                    decision_reason_codes=["AMBIGUOUS"],
                    confidence=0.5,
                    notes="Candidate omitted by LLM; defaulting to SEPARATE_EVENT",
                )

            if (
                d.decision == "SAME_EVENT"
                and d.confidence < config.adjudication.needs_review_confidence_cutoff
            ):
                d.decision = "NEEDS_REVIEW"
                if "AMBIGUOUS" not in d.decision_reason_codes:
                    d.decision_reason_codes.append("AMBIGUOUS")

            normalized_batch_decisions.append(d)

        all_decisions.extend(normalized_batch_decisions)

    return all_decisions
