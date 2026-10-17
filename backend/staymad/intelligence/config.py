"""Configuration loader for Importance Scoring Algorithm.

Authority: docs/architecture/G-importance-algorithm.md (§53-G), decisions.md Conflict #1, config/importance.yaml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "importance.yaml"


@dataclass
class ImportanceWeights:
    impact: float = 0.30
    urgency: float = 0.20
    proximity: float = 0.15
    public_importance: float = 0.15
    momentum: float = 0.20


@dataclass
class ImportanceThresholds:
    high: float = 0.70
    medium: float = 0.40
    low: float = 0.0


@dataclass
class ImportanceConfig:
    weights: ImportanceWeights
    thresholds: ImportanceThresholds
    impact_signals: list[dict[str, Any]] = field(default_factory=list)
    proximity_scores: dict[str, float] = field(default_factory=dict)
    public_importance: dict[str, Any] = field(default_factory=dict)
    momentum: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> ImportanceConfig:
        config_file = path or DEFAULT_CONFIG_PATH
        if not config_file.exists():
            return cls(
                weights=ImportanceWeights(),
                thresholds=ImportanceThresholds(),
            )

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        raw_weights = data.get("weights", {})
        weights = ImportanceWeights(
            impact=float(raw_weights.get("impact", 0.30)),
            urgency=float(raw_weights.get("urgency", 0.20)),
            proximity=float(raw_weights.get("proximity", 0.15)),
            public_importance=float(raw_weights.get("public_importance", 0.15)),
            momentum=float(raw_weights.get("momentum", 0.20)),
        )

        raw_thresh = data.get("thresholds", {})
        thresholds = ImportanceThresholds(
            high=float(raw_thresh.get("high", 0.70)),
            medium=float(raw_thresh.get("medium", 0.40)),
            low=float(raw_thresh.get("low", 0.0)),
        )

        return cls(
            weights=weights,
            thresholds=thresholds,
            impact_signals=data.get("impact_signals", []),
            proximity_scores=data.get("proximity_scores", {}),
            public_importance=data.get("public_importance", {}),
            momentum=data.get("momentum", {}),
        )
