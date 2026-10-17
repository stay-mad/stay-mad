"""Configuration loader for Confidence Scoring Algorithm.

Authority: docs/architecture/F-confidence-algorithm.md (§53-F), config/confidence.yaml
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "confidence.yaml"


@dataclass
class ConfidenceWeights:
    source_quality: float = 0.30
    corroboration: float = 0.25
    claim_consistency: float = 0.20
    official_confirmation: float = 0.15
    temporal_consistency: float = 0.10


@dataclass
class ConfidenceThresholds:
    high: float = 0.70
    medium: float = 0.45
    flag_for_human_review: float = 0.40


@dataclass
class ConfidenceConfig:
    weights: ConfidenceWeights
    thresholds: ConfidenceThresholds
    corroboration_max_families: int = 4

    @classmethod
    def load(cls, path: Path | None = None) -> ConfidenceConfig:
        config_file = path or DEFAULT_CONFIG_PATH
        if not config_file.exists():
            return cls(
                weights=ConfidenceWeights(),
                thresholds=ConfidenceThresholds(),
                corroboration_max_families=4,
            )

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        raw_weights = data.get("weights", {})
        weights = ConfidenceWeights(
            source_quality=float(raw_weights.get("source_quality", 0.30)),
            corroboration=float(raw_weights.get("corroboration", 0.25)),
            claim_consistency=float(raw_weights.get("claim_consistency", 0.20)),
            official_confirmation=float(raw_weights.get("official_confirmation", 0.15)),
            temporal_consistency=float(raw_weights.get("temporal_consistency", 0.10)),
        )

        raw_thresh = data.get("thresholds", {})
        thresholds = ConfidenceThresholds(
            high=float(raw_thresh.get("high", 0.70)),
            medium=float(raw_thresh.get("medium", 0.45)),
            flag_for_human_review=float(raw_thresh.get("flag_for_human_review", 0.40)),
        )

        corrob_max = int(data.get("corroboration_max_families", 4))

        return cls(
            weights=weights,
            thresholds=thresholds,
            corroboration_max_families=corrob_max,
        )
