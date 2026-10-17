"""Timeline Reconstruction and Temporal Sorting Module.

Authority: docs/architecture/E-timeline-algorithm.md (§53-E), DEC-0001
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from backend.staymad.db.models.enums import TimelinePrecision
from backend.staymad.db.models.timeline import TimelineEntry

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

MONTH_NAMES_ID = [
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]


def format_timeline_display_time(
    event_time: datetime | None,
    precision: TimelinePrecision | str = TimelinePrecision.EXACT,
    qualifier: str | None = None,
    published_time: datetime | None = None,
) -> str:
    """Format event time into canonical Indonesian UI display per §53-E §4 and DEC-0001.

    Precision display rules:
    - EXACT: "08:10 WIB"
    - APPROXIMATE: "Sekitar 08:10 WIB" (or capitalized qualifier)
    - DAY: "10 Oktober 2026"
    - RANGE: "08:00–10:00 WIB"
    - UNKNOWN: "Waktu tidak diketahui (dilaporkan ~14:00 WIB)"
    """
    prec_str = (
        precision.value if isinstance(precision, TimelinePrecision) else str(precision)
    ).upper()

    if event_time is None:
        if published_time is not None:
            pub_local = published_time.astimezone(JAKARTA_TZ)
            return (
                f"Waktu tidak diketahui (dilaporkan ~{pub_local.strftime('%H:%M')} WIB)"
            )
        return "Waktu tidak diketahui"

    local_dt = event_time.astimezone(JAKARTA_TZ)

    if prec_str == "DAY":
        month_name = MONTH_NAMES_ID[local_dt.month]
        date_str = f"{local_dt.day} {month_name} {local_dt.year}"
        if qualifier:
            return f"{qualifier.capitalize()} {date_str}"
        return date_str

    time_str = f"{local_dt.strftime('%H:%M')} WIB"

    if prec_str == "APPROXIMATE":
        q = (qualifier or "sekitar").capitalize()
        return f"{q} {time_str}"

    if prec_str == "RANGE":
        return time_str

    if qualifier:
        return f"{qualifier.capitalize()} {time_str}"

    return time_str


def deduplicate_temporal_claims(claims: list[Claim]) -> list[Claim]:
    """Deduplicate temporal claims from identical source_family at identical event_time.

    Authority: §53-E Step 3 (corroboration grouping).
    """
    deduped: list[Claim] = []
    seen: dict[tuple[str, str | None], Claim] = {}

    for c in claims:
        # Determine source_family
        fam = "UNKNOWN"
        if c.source and c.source.source_family:
            fam = c.source.source_family

        time_key = (
            c.event_time.isoformat() if c.event_time is not None else c.event_time_raw
        )
        key = (fam, time_key)

        if time_key is not None and key in seen:
            # Same family and same time -> keep higher precision or higher tier
            existing = seen[key]
            # If current has higher extraction confidence, update
            if c.extraction_confidence > existing.extraction_confidence:
                seen[key] = c
        else:
            if time_key is not None:
                seen[key] = c
            deduped.append(c)

    # Reassemble in order of appearance
    final_claims: list[Claim] = []
    added_ids = set()
    for c in claims:
        time_key = (
            c.event_time.isoformat() if c.event_time is not None else c.event_time_raw
        )
        fam = (
            c.source.source_family
            if (c.source and c.source.source_family)
            else "UNKNOWN"
        )
        key = (fam, time_key)
        winner = seen.get(key, c)
        if winner.id not in added_ids:
            added_ids.add(winner.id)
            final_claims.append(winner)

    return final_claims


def build_timeline_entries(
    claims: list[Claim],
    event_id: uuid.UUID,
    snapshot_id: uuid.UUID,
) -> list[TimelineEntry]:
    """Reconstruct chronological timeline from claims per §53-E Step 5.

    1. Separate known_time vs unknown_time.
    2. Sort known_time chronologically (event_time ASC).
    3. Sort unknown_time by published_time (fallback proxy).
    4. Assemble TimelineEntry records with preserved qualifiers.
    """
    if not claims:
        return []

    # Step 3: Deduplicate
    unique_claims = deduplicate_temporal_claims(claims)

    # Step 5: Assembly
    known_time = [c for c in unique_claims if c.event_time is not None]
    unknown_time = [c for c in unique_claims if c.event_time is None]

    # Sort known_time ASC
    def sort_known_key(c: Claim) -> tuple[datetime, datetime, str]:
        evt_t = c.event_time or datetime.min.replace(tzinfo=UTC)
        pub_t = (
            c.article_version.published_time
            if (c.article_version and c.article_version.published_time)
            else evt_t
        )
        return (evt_t, pub_t, str(c.id))

    known_time.sort(key=sort_known_key)

    # Sort unknown_time by published_time (fallback proxy)
    def sort_unknown_key(c: Claim) -> tuple[datetime, str]:
        pub_t = (
            c.article_version.published_time
            if (c.article_version and c.article_version.published_time)
            else c.created_at
        )
        return (pub_t, str(c.id))

    unknown_time.sort(key=sort_unknown_key)

    ordered = known_time + unknown_time

    entries: list[TimelineEntry] = []
    for i, c in enumerate(ordered):
        t_event = c.event_time
        prec = c.event_time_precision
        qual = c.event_time_qualifier

        if t_event is None and c.article_version and c.article_version.published_time:
            t_event = c.article_version.published_time
            if prec == TimelinePrecision.UNKNOWN:
                prec = TimelinePrecision.APPROXIMATE
            if not qual:
                qual = "dilaporkan pada"

        entry = TimelineEntry(
            id=uuid.uuid4(),
            event_id=event_id,
            snapshot_id=snapshot_id,
            event_time=t_event,
            event_time_precision=prec,
            event_time_qualifier=qual,
            description=c.claim_text,
            evidence_claim_ids=[str(c.id)],
            order_index=i,
        )
        entries.append(entry)

    return entries
