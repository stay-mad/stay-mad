"""Configuration loader and schema for Stay Mad 3-Tier Event Resolver.

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D), config/resolver.yaml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "resolver.yaml"


@dataclass
class HardConstraintConfig:
    time_incompatible_hours: float = 72.0
    location_incompatible_km: float | None = None
    strict_category: bool = True
    type_exclusion_rules: list[list[str]] = field(default_factory=list)


@dataclass
class EmbeddingConfig:
    top_k: int = 10
    min_cosine: float = 0.20
    model_name: str = "text-multilingual-embedding-002"
    vector_dimension: int = 768


@dataclass
class ScoringWeightsConfig:
    w_semantic: float = 0.40
    w_time: float = 0.30
    w_location: float = 0.20
    w_entity: float = 0.10
    time_decay_hours: float = 48.0


@dataclass
class ThresholdsConfig:
    low: float = 0.35
    high: float = 0.75


@dataclass
class AdjudicationConfig:
    max_candidates_per_call: int = 5
    needs_review_confidence_cutoff: float = 0.60


@dataclass
class ResolverConfig:
    hard: HardConstraintConfig = field(default_factory=HardConstraintConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    scoring: ScoringWeightsConfig = field(default_factory=ScoringWeightsConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    adjudication: AdjudicationConfig = field(default_factory=AdjudicationConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResolverConfig:
        res_data = data.get("resolver", {})

        hard_data = res_data.get("hard", {})
        hard_cfg = HardConstraintConfig(
            time_incompatible_hours=float(
                hard_data.get("time_incompatible_hours", 72.0)
            ),
            location_incompatible_km=hard_data.get("location_incompatible_km"),
            strict_category=bool(hard_data.get("strict_category", True)),
            type_exclusion_rules=list(hard_data.get("type_exclusion_rules", [])),
        )

        emb_data = res_data.get("embedding", {})
        emb_cfg = EmbeddingConfig(
            top_k=int(emb_data.get("top_k", 10)),
            min_cosine=float(emb_data.get("min_cosine", 0.20)),
            model_name=str(
                emb_data.get("model_name", "text-multilingual-embedding-002")
            ),
            vector_dimension=int(emb_data.get("vector_dimension", 768)),
        )

        sc_data = res_data.get("scoring", {})
        sc_cfg = ScoringWeightsConfig(
            w_semantic=float(sc_data.get("w_semantic", 0.40)),
            w_time=float(sc_data.get("w_time", 0.30)),
            w_location=float(sc_data.get("w_location", 0.20)),
            w_entity=float(sc_data.get("w_entity", 0.10)),
            time_decay_hours=float(sc_data.get("time_decay_hours", 48.0)),
        )

        th_data = res_data.get("thresholds", {})
        th_cfg = ThresholdsConfig(
            low=float(th_data.get("low", 0.35)),
            high=float(th_data.get("high", 0.75)),
        )

        adj_data = res_data.get("adjudication", {})
        adj_cfg = AdjudicationConfig(
            max_candidates_per_call=int(adj_data.get("max_candidates_per_call", 5)),
            needs_review_confidence_cutoff=float(
                adj_data.get("needs_review_confidence_cutoff", 0.60)
            ),
        )

        return cls(
            hard=hard_cfg,
            embedding=emb_cfg,
            scoring=sc_cfg,
            thresholds=th_cfg,
            adjudication=adj_cfg,
        )

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> ResolverConfig:
        target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if not target_path.exists():
            return cls()
        with open(target_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls.from_dict(raw)
