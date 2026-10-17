"""Deterministic Importance Scoring Calculator.

Authority: docs/architecture/G-importance-algorithm.md (§53-G), decisions.md Conflict #1
Single source of truth: config/importance.yaml
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.staymad.db.models.enums import ActionabilityLevel
from backend.staymad.intelligence.config import ImportanceConfig

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim
    from backend.staymad.db.models.event import Event


@dataclass
class ImportanceResult:
    """Outcome of importance scoring with component breakdown and UI label."""

    importance_score: float
    urgency_score: float
    ui_label: str
    components: dict[str, float]
    signals: list[str]


def calculate_importance(
    event: Event,
    claims: list[Claim],
    latest_update_time: datetime | None = None,
    snapshots_count_6h: int = 1,
    new_claims_count_6h: int = 0,
    actionability_level: ActionabilityLevel = ActionabilityLevel.INFORMATIONAL,
    config: ImportanceConfig | None = None,
) -> ImportanceResult:
    """Calculate deterministic importance_score and urgency_score per §53-G.

    CRITICAL: confidence_score is NOT a component of importance_score (Conflict #1).
    """
    cfg = config or ImportanceConfig.load()
    signals: list[str] = []

    # 1. impact_score (§53-G §2.1)
    combined_text = " ".join(c.claim_text for c in claims).lower()
    impact_score = 0.20  # default informatif

    if any(
        w in combined_text
        for w in (
            "korban jiwa",
            "evakuasi massal",
            "posko pengungsian",
            "segera melakukan evakuasi",
        )
    ):
        impact_score = 1.00
        signals.append("Evakuasi massal / keselamatan jiwa aktif")
    elif any(
        w in combined_text
        for w in (
            "gangguan persinyalan",
            "stasiun manggarai",
            "jalur tol",
            "bandara",
            "rel kereta",
        )
    ):
        impact_score = 0.85
        signals.append("Infrastruktur transportasi kritis terdampak")
    elif any(
        w in combined_text
        for w in (
            "siaga 2",
            "siaga 1",
            "level iii",
            "level iv",
            "erupsi merapi",
            "banjir rendam",
        )
    ):
        impact_score = 0.80
        signals.append("Status siaga kebencanaan resmi aktif")
    elif any(
        w in combined_text
        for w in ("rekayasa pola operasi", "penumpukan penumpang", "antrean panjang")
    ):
        impact_score = 0.65
        signals.append("Gangguan transportasi signifikan")
    elif any(
        w in combined_text
        for w in ("perpres", "subsidi", "tarif integrasi", "skema baru subsidi")
    ):
        impact_score = 0.60
        signals.append("Kebijakan publik dengan dampak masyarakat luas")
    elif any(
        w in combined_text
        for w in ("genangan pasang rob", "pompa stasioner", "layanan minor")
    ):
        impact_score = 0.40
        signals.append("Dampak layanan publik terlokalisir")

    # 2. urgency_score (§53-G §2.2)
    ref_time = latest_update_time or event.updated_at
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=UTC)
    now = datetime.now(UTC)

    hours_since_update = max(0.0, (now - ref_time).total_seconds() / 3600.0)

    if actionability_level in (
        ActionabilityLevel.ACTION_REQUIRED,
        ActionabilityLevel.ACTION_RECOMMENDED,
    ):
        recency_factor = max(0.0, 1.0 - hours_since_update / 24.0)
        urgency_score = min(1.0, 0.70 + recency_factor * 0.30)
        signals.append("Instruksi aksi resmi memerlukan perhatian segera")
    elif hours_since_update < 2.0:
        urgency_score = 0.60
        signals.append("Peristiwa baru berkembang dalam 2 jam terakhir")
    elif hours_since_update < 8.0:
        urgency_score = 0.40
    elif hours_since_update < 24.0:
        urgency_score = 0.20
    else:
        urgency_score = 0.05

    # 3. proximity_score (§53-G §2.3)
    # Default location: Jakarta (DEC-0001)
    loc_text = ""
    if event.primary_location:
        loc_text = f"{event.primary_location.city or ''} {event.primary_location.province or ''}".lower()
    else:
        loc_text = combined_text

    if any(
        w in loc_text
        for w in (
            "jakarta timur",
            "jakarta barat",
            "jakarta selatan",
            "jakarta pusat",
            "jakarta utara",
            "manggarai",
            "ciliwung",
            "cipinang",
        )
    ):
        proximity_score = 1.00
        signals.append("Lokasi primer di wilayah metropolitan Jakarta")
    elif "dki jakarta" in loc_text or "jakarta" in loc_text:
        proximity_score = 0.75
        signals.append("Wilayah provinsi DKI Jakarta")
    elif any(
        w in loc_text
        for w in ("sleman", "yogyakarta", "merapi", "jawa tengah", "indonesia")
    ):
        proximity_score = 0.50
        signals.append("Skala nasional / regional Indonesia")
    elif any(
        w in loc_text for w in ("asean", "asia tenggara", "singapura", "malaysia")
    ):
        proximity_score = 0.25
    else:
        proximity_score = 0.50  # default national

    # 4. public_importance_score (§53-G §2.4)
    public_imp = 0.0
    has_gov = any(
        (c.source and c.source.source_family.startswith("GOV_")) for c in claims
    )
    if has_gov:
        public_imp += cfg.public_importance.get("gov_source_weight", 0.40)
        signals.append("Dikonfirmasi oleh otoritas resmi pemerintah")

    unique_fams = {
        c.source.source_family
        for c in claims
        if c.source and c.source.source_family and c.source.source_family != "UNKNOWN"
    }
    per_fam_weight = cfg.public_importance.get("per_unique_family_weight", 0.10)
    public_imp += min(0.40, len(unique_fams) * per_fam_weight)

    cat_val = (
        event.category.value
        if hasattr(event.category, "value")
        else str(event.category)
    )
    cat_lower = cat_val.lower()
    cat_base_scores = cfg.public_importance.get("category_base_scores", {})
    cat_bonus = cat_base_scores.get(cat_lower, cat_base_scores.get("default", 0.10))
    public_imp += cat_bonus
    public_importance_score = min(1.0, public_imp)

    # 5. momentum_score (§53-G §2.5)
    snap_signal = min(
        1.0, snapshots_count_6h / float(cfg.momentum.get("snapshot_normalization", 3))
    )
    clm_signal = min(
        1.0,
        (new_claims_count_6h or len(claims))
        / float(cfg.momentum.get("claim_normalization", 10)),
    )
    momentum_score = round(0.5 * snap_signal + 0.5 * clm_signal, 4)
    if momentum_score >= 0.60:
        signals.append("Aktivitas pembaruan intensif dalam 6 jam terakhir")

    # Formula weighted sum (§53-G §2)
    raw_importance = (
        cfg.weights.impact * impact_score
        + cfg.weights.urgency * urgency_score
        + cfg.weights.proximity * proximity_score
        + cfg.weights.public_importance * public_importance_score
        + cfg.weights.momentum * momentum_score
    )
    importance_score = round(min(1.0, max(0.0, raw_importance)), 4)
    urgency_score = round(min(1.0, max(0.0, urgency_score)), 4)

    # Derive UI label (§53-G §4)
    if importance_score >= cfg.thresholds.high and urgency_score >= 0.60:
        ui_label = "NEED TO KNOW"
    elif importance_score >= cfg.thresholds.high:
        ui_label = "HIGH IMPACT"
    elif actionability_level == ActionabilityLevel.ACTION_REQUIRED:
        ui_label = "ACTION REQUIRED"
    elif momentum_score >= 0.60:
        ui_label = "DEVELOPING"
    elif importance_score < cfg.thresholds.medium and momentum_score < 0.30:
        ui_label = "INFORMATIONAL"
    else:
        ui_label = "MEDIUM"

    return ImportanceResult(
        importance_score=importance_score,
        urgency_score=urgency_score,
        ui_label=ui_label,
        components={
            "impact": round(impact_score, 4),
            "urgency": round(urgency_score, 4),
            "proximity": round(proximity_score, 4),
            "public_importance": round(public_importance_score, 4),
            "momentum": round(momentum_score, 4),
        },
        signals=signals,
    )
