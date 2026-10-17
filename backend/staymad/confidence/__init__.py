"""Confidence Scoring package.

Authority: docs/architecture/F-confidence-algorithm.md (§53-F), config/confidence.yaml
"""

from backend.staymad.confidence.calculator import (
    ConfidenceResult,
    calculate_confidence,
)
from backend.staymad.confidence.config import (
    ConfidenceConfig,
    ConfidenceThresholds,
    ConfidenceWeights,
)

__all__ = [
    "ConfidenceConfig",
    "ConfidenceResult",
    "ConfidenceThresholds",
    "ConfidenceWeights",
    "calculate_confidence",
]
