"""Grounding and verbatim quote verification gates.

Authority: docs/architecture/C-gemini-architecture.md §53-C Validasi 1 & 4
"""

from __future__ import annotations

from typing import Any

from backend.staymad.llm.schemas import ExtractedClaim
from backend.staymad.normalize.text import verbatim_substring_match


class QuoteVerificationResult:
    """Result of validating a claim's source_span against original article text."""

    def __init__(
        self,
        is_grounded: bool,
        match_score: float,
        adjusted_confidence: float,
        reason: str | None = None,
    ) -> None:
        self.is_grounded = is_grounded
        self.match_score = match_score
        self.adjusted_confidence = adjusted_confidence
        self.reason = reason


def verify_claim_grounding(
    claim: ExtractedClaim | dict[str, Any],
    article_text: str,
    min_fuzzy_ratio: float = 0.85,
) -> QuoteVerificationResult:
    """Verify that a claim's source_span exists verbatim in the original article.

    1. Enforces length < 200 characters.
    2. Enforces substring match >= min_fuzzy_ratio (85%).
    3. Downgrades confidence or rejects hallucinated quotes.
    """
    source_span = (
        claim.source_span
        if isinstance(claim, ExtractedClaim)
        else claim.get("source_span", "")
    )
    confidence = (
        claim.extraction_confidence
        if isinstance(claim, ExtractedClaim)
        else claim.get("extraction_confidence", 0.9)
    )

    # 1. Enforce length constraint (< 200 chars)
    if len(source_span) >= 200:
        return QuoteVerificationResult(
            is_grounded=False,
            match_score=0.0,
            adjusted_confidence=0.0,
            reason=f"DEC-0004: source_span exceeds 200 characters limit ({len(source_span)} chars)",
        )

    if not source_span.strip():
        return QuoteVerificationResult(
            is_grounded=False,
            match_score=0.0,
            adjusted_confidence=0.0,
            reason="Empty source_span",
        )

    # 2. Check verbatim match in article text
    matched, score = verbatim_substring_match(
        source_span, article_text, min_fuzzy_ratio=min_fuzzy_ratio
    )

    if not matched:
        # Hallucination / ungrounded claim -> drop or severely downgrade
        return QuoteVerificationResult(
            is_grounded=False,
            match_score=score,
            adjusted_confidence=min(confidence * 0.3, 0.3),
            reason=f"Ungrounded: source_span not found in article text (overlap ratio: {score:.2f})",
        )

    # If partial fuzzy match (0.85 <= score < 1.0), adjust confidence proportionally
    adjusted = confidence * score
    return QuoteVerificationResult(
        is_grounded=True,
        match_score=score,
        adjusted_confidence=adjusted,
        reason="Verified verbatim quote",
    )


def filter_and_gate_claims(
    claims: list[ExtractedClaim],
    article_text: str,
    min_confidence: float = 0.5,
) -> tuple[list[ExtractedClaim], list[dict[str, Any]]]:
    """Apply verbatim quote gate and confidence thresholding to a batch of claims.

    Returns:
        (accepted_claims, rejected_claims_info)
    """
    accepted: list[ExtractedClaim] = []
    rejected: list[dict[str, Any]] = []

    for c in claims:
        verif = verify_claim_grounding(c, article_text)
        if not verif.is_grounded or verif.adjusted_confidence < min_confidence:
            rejected.append(
                {
                    "claim_text": c.claim_text,
                    "source_span": c.source_span,
                    "reason": verif.reason,
                    "score": verif.match_score,
                    "original_confidence": c.extraction_confidence,
                    "adjusted_confidence": verif.adjusted_confidence,
                }
            )
        else:
            # Update claim with adjusted confidence
            c.extraction_confidence = round(verif.adjusted_confidence, 3)
            accepted.append(c)

    return accepted, rejected
