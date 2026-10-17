"""Tier 1: Deterministic Matching, Hard Constraints, Content Dedup, and Source Family Grouping.

Authority: docs/architecture/D-event-resolution-algorithm.md (§53-D), ADR-005
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from backend.staymad.resolver.config import ResolverConfig


@dataclass
class ArticleCandidate:
    """Normalized article candidate for resolution pipeline."""

    article_version_id: str
    article_id: str | None = None
    title: str = ""
    excerpt: str = ""
    category: str = "disaster_and_weather"
    event_time: datetime | None = None
    published_time: datetime | None = None
    location_raw: str | None = None
    province: str | None = None
    city: str | None = None
    entities: list[str] = field(default_factory=list)
    source_family: str = "UNKNOWN"
    source_tier: str = "TIER_2"
    content_hash: str | None = None
    claims_text: list[str] = field(default_factory=list)
    embedding: list[float] | None = None


@dataclass
class EventAnchor:
    """Canonical representation of an existing event for resolution."""

    event_id: str
    event_type: str = "GENERAL"
    category: str = "disaster_and_weather"
    headline: str = ""
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    time_window_center: datetime | None = None
    primary_location_name: str | None = None
    province: str | None = None
    city: str | None = None
    entities: list[str] = field(default_factory=list)
    representative_claims: list[str] = field(default_factory=list)
    source_families: set[str] = field(default_factory=set)
    embedding: list[float] | None = None
    article_version_ids: list[str] = field(default_factory=list)


def normalize_text(text: str) -> str:
    """Normalize text for deterministic hashing and token matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def compute_content_hash(title: str, excerpt: str) -> str:
    """Compute sha256(normalize(title + excerpt)) per §53-D."""
    norm = normalize_text(f"{title} {excerpt}")
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def is_content_duplicate(content_hash: str, existing_hashes: set[str]) -> bool:
    """Check if content hash already exists in processed pool."""
    return content_hash in existing_hashes


def extract_indonesian_region(text: str | None) -> tuple[str | None, str | None]:
    """Extract province and city/regency from Indonesian location text or raw mention."""
    if not text:
        return None, None

    lower = text.lower()

    # Province detection (check specific regions first before generic Jakarta dateline)
    province: str | None = None
    if any(
        k in lower
        for k in (
            "di yogyakarta",
            "yogyakarta",
            "jogja",
            "sleman",
            "bantul",
            "kulon progo",
            "gunungkidul",
        )
    ):
        province = "DI Yogyakarta"
    elif any(
        k in lower
        for k in (
            "jawa tengah",
            "jateng",
            "magelang",
            "boyolali",
            "klaten",
            "merapi",
            "semarang",
            "solo",
            "surakarta",
            "demak",
            "kudus",
        )
    ):
        province = "Jawa Tengah"
    elif any(
        k in lower
        for k in (
            "jawa barat",
            "jabar",
            "bogor",
            "depok",
            "gandul",
            "bekasi",
            "bandung",
            "sumedang",
            "cadas pangeran",
            "puncak",
        )
    ):
        province = "Jawa Barat"
    elif any(k in lower for k in ("banten", "tangerang", "serang", "cilegon")):
        province = "Banten"
    elif any(k in lower for k in ("dki jakarta", "jakarta")):
        province = "DKI Jakarta"

    # City / Regency / District detection within province
    city: str | None = None
    if any(
        k in lower
        for k in (
            "jakarta timur",
            "jaktim",
            "cipinang melayu",
            "kampung melayu",
            "ciliwung",
            "cawang",
            "cililitan",
            "jatinegara",
            "bidara cina",
            "tol dalam kota",
        )
    ):
        city = "Jakarta Timur"
    elif any(
        k in lower
        for k in (
            "jakarta barat",
            "jakbar",
            "rawa buaya",
            "kamal muara",
            "cengkareng",
            "kebon jeruk",
            "grogol",
        )
    ):
        city = "Jakarta Barat"
    elif any(
        k in lower
        for k in (
            "jakarta selatan",
            "jaksel",
            "manggarai",
            "tebet",
            "kebayoran",
            "pasar minggu",
        )
    ):
        city = "Jakarta Selatan"
    elif any(
        k in lower
        for k in (
            "jakarta pusat",
            "jakpus",
            "gambir",
            "monas",
            "senen",
            "tanah abang",
            "istana negara",
            "bundaran hi",
            "kemenhub",
            "setkab",
            "kemenko",
            "sidang kabinet",
            "presiden",
        )
    ):
        city = "Jakarta Pusat"
    elif any(
        k in lower
        for k in ("jakarta utara", "jakut", "tanjung priok", "ancol", "pluit")
    ):
        city = "Jakarta Utara"
    elif "sleman" in lower:
        city = "Sleman"
    elif "bantul" in lower or "parangtritis" in lower:
        city = "Bantul"
    elif "yogyakarta" in lower or "jogja" in lower:
        city = "Yogyakarta"
    elif "demak" in lower:
        city = "Demak"
    elif "sumedang" in lower or "cadas pangeran" in lower:
        city = "Sumedang"
    elif "bogor" in lower or "puncak" in lower:
        city = "Bogor"
    elif "depok" in lower or "gandul" in lower:
        city = "Depok"
    elif any(k in lower for k in ("merapi", "magelang", "boyolali", "klaten")):
        city = "Kawasan Merapi"

    # Enforce hierarchical consistency between city and province
    if city in (
        "Jakarta Timur",
        "Jakarta Barat",
        "Jakarta Selatan",
        "Jakarta Pusat",
        "Jakarta Utara",
    ):
        province = "DKI Jakarta"
    elif city in ("Sleman", "Bantul", "Yogyakarta"):
        province = "DI Yogyakarta"
    elif city in ("Bogor", "Depok", "Sumedang"):
        province = "Jawa Barat"
    elif city in ("Demak",):
        province = "Jawa Tengah"
    elif city == "Kawasan Merapi":
        if any(k in lower for k in ("sleman", "yogyakarta", "jogja")):
            province = "DI Yogyakarta"
        else:
            province = "Jawa Tengah"

    if province == "DKI Jakarta" and city is None:
        city = "Jakarta Pusat"

    return province, city


def is_location_incompatible(
    cand_prov: str | None,
    cand_city: str | None,
    anchor_prov: str | None,
    anchor_city: str | None,
) -> bool:
    """Determine if candidate and anchor locations are strictly incompatible.

    Rules:
    1. If both provinces are known and distinct -> incompatible.
    2. If both cities are known and distinct within the same province
       (e.g., Jakarta Barat vs Jakarta Timur in localized flood events) -> incompatible.
    3. If one or both are unknown -> compatible (do not reject early).
    """
    if cand_prov and anchor_prov and cand_prov.lower() != anchor_prov.lower():
        return True

    # Check distinct cities/districts when both specified
    return bool(cand_city and anchor_city and cand_city.lower() != anchor_city.lower())


def to_utc(dt: datetime | None) -> datetime | None:
    """Normalize datetime to UTC for timezone-safe comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(
            tzinfo=datetime.now().astimezone().tzinfo or datetime.min.tzinfo
        ).astimezone(datetime.now().astimezone().tzinfo)
    return dt


def check_hard_constraints(
    candidate: ArticleCandidate,
    anchor: EventAnchor,
    config: ResolverConfig,
) -> tuple[bool, str | None]:
    """Check Tier 1 hard constraints.

    Returns:
        (True, None) if all hard constraints pass.
        (False, reason_code) if any constraint fails, where reason_code is one of:
        - LOC_INCOMPATIBLE
        - TIME_INCOMPATIBLE
        - CAT_MISMATCH
        - TYPE_EXCLUSIVE
    """
    # 1. CAT_MISMATCH check
    if config.hard.strict_category:
        cand_cat = candidate.category.lower().strip()
        anchor_cat = anchor.category.lower().strip()
        if cand_cat != anchor_cat:
            return False, "CAT_MISMATCH"

    # 2. TIME_INCOMPATIBLE check
    cand_time = candidate.event_time or candidate.published_time
    anchor_time = (
        anchor.time_window_center or anchor.time_window_start or anchor.time_window_end
    )

    if cand_time and anchor_time:
        t_cand = (
            cand_time
            if cand_time.tzinfo
            else cand_time.replace(tzinfo=anchor_time.tzinfo)
        )
        t_anc = (
            anchor_time
            if anchor_time.tzinfo
            else anchor_time.replace(tzinfo=cand_time.tzinfo)
        )
        delta_hours = abs((t_cand - t_anc).total_seconds()) / 3600.0
        if delta_hours > config.hard.time_incompatible_hours:
            return False, "TIME_INCOMPATIBLE"

    # 3. LOC_INCOMPATIBLE check
    cand_prov, cand_city = candidate.province, candidate.city
    if not cand_prov or not cand_city:
        p_guess, c_guess = extract_indonesian_region(
            candidate.location_raw or f"{candidate.title} {candidate.excerpt}"
        )
        cand_prov = cand_prov or p_guess
        cand_city = cand_city or c_guess

    anchor_prov, anchor_city = anchor.province, anchor.city
    if not anchor_prov or not anchor_city:
        p_guess, c_guess = extract_indonesian_region(
            anchor.primary_location_name or anchor.headline
        )
        anchor_prov = anchor_prov or p_guess
        anchor_city = anchor_city or c_guess

    if is_location_incompatible(cand_prov, cand_city, anchor_prov, anchor_city):
        return False, "LOC_INCOMPATIBLE"

    # 4. TYPE_EXCLUSIVE check
    for pair in config.hard.type_exclusion_rules:
        if len(pair) == 2:
            t1, t2 = pair[0].lower(), pair[1].lower()
            c_type = getattr(candidate, "event_type", "").lower()
            a_type = anchor.event_type.lower()
            if (c_type == t1 and a_type == t2) or (c_type == t2 and a_type == t1):
                return False, "TYPE_EXCLUSIVE"

    return True, None


def group_candidates_by_source_family(
    candidates: list[ArticleCandidate],
) -> dict[str, list[ArticleCandidate]]:
    """Group article candidates by source_family to prevent consensus inflation.

    Articles from the same media group (e.g. TRANSMEDIA: Detik + CNN Indonesia)
    count as 1 family corroboration signal.
    """
    grouped: dict[str, list[ArticleCandidate]] = {}
    for cand in candidates:
        grouped.setdefault(cand.source_family, []).append(cand)
    return grouped


def filter_candidate_events(
    candidate: ArticleCandidate,
    anchors: list[EventAnchor],
    config: ResolverConfig,
) -> list[tuple[EventAnchor, str | None]]:
    """Filter candidate events for an incoming article through Tier 1 hard constraints.

    Returns list of (anchor, failure_reason_code_if_any).
    """
    results: list[tuple[EventAnchor, str | None]] = []
    for anchor in anchors:
        passed, reason = check_hard_constraints(candidate, anchor, config)
        if passed:
            results.append((anchor, None))
        else:
            results.append((anchor, reason))
    return results
