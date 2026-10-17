"""Event Resolution & Canonical Clustering module (3-Tier Hybrid Resolver).

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D), ADR-005
"""

from __future__ import annotations

from backend.staymad.resolver.audit import create_and_persist_membership_audit
from backend.staymad.resolver.config import ResolverConfig
from backend.staymad.resolver.manager import EventResolverManager, ResolutionResult
from backend.staymad.resolver.tier1_deterministic import (
    ArticleCandidate,
    EventAnchor,
    check_hard_constraints,
    compute_content_hash,
    extract_indonesian_region,
    filter_candidate_events,
    group_candidates_by_source_family,
    is_content_duplicate,
    is_location_incompatible,
)
from backend.staymad.resolver.tier2_embedding import (
    BaseEmbeddingGenerator,
    DeterministicEmbeddingGenerator,
    GeminiEmbeddingGenerator,
    compute_composite_score,
    cosine_similarity,
    evaluate_tier2_threshold,
    get_embedding_generator,
)
from backend.staymad.resolver.tier3_adjudicate import adjudicate_candidates

__all__ = [
    "ArticleCandidate",
    "BaseEmbeddingGenerator",
    "DeterministicEmbeddingGenerator",
    "EventAnchor",
    "EventResolverManager",
    "GeminiEmbeddingGenerator",
    "ResolutionResult",
    "ResolverConfig",
    "adjudicate_candidates",
    "check_hard_constraints",
    "compute_composite_score",
    "compute_content_hash",
    "cosine_similarity",
    "create_and_persist_membership_audit",
    "evaluate_tier2_threshold",
    "extract_indonesian_region",
    "filter_candidate_events",
    "get_embedding_generator",
    "group_candidates_by_source_family",
    "is_content_duplicate",
    "is_location_incompatible",
]
