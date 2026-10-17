"""Temporal normalization and formatting to ISO-8601 UTC and Asia/Jakarta display.

Authority: docs/architecture/E-timeline-algorithm.md §53-E, DEC-0001
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from backend.staymad.db.models.enums import TimelinePrecision, TimelineQualifier

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")
UTC_TZ = UTC

MONTH_MAP_ID = {
    "januari": 1,
    "jan": 1,
    "februari": 2,
    "feb": 2,
    "maret": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mei": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "agustus": 8,
    "agu": 8,
    "agt": 8,
    "september": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "november": 11,
    "nov": 11,
    "desember": 12,
    "des": 12,
}


def parse_datetime_flexible(val: Any) -> datetime | None:
    """Parse various string or datetime formats into a timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=JAKARTA_TZ)
        return val

    s = str(val).strip()
    if not s:
        return None

    # Try standard ISO-8601
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JAKARTA_TZ)
        return dt
    except ValueError:
        pass

    # Try regex patterns like "2026-10-10 09:30:00"
    m = re.search(
        r"(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?", s
    )
    if m:
        year, month, day, hour, minute = map(int, m.groups()[:5])
        sec = int(m.group(6)) if m.group(6) else 0
        return datetime(year, month, day, hour, minute, sec, tzinfo=JAKARTA_TZ)

    return None


def extract_qualifier(text: str) -> tuple[str | None, str]:
    """Extract canonical qualifier and stripped text."""
    lower = text.lower()
    qualifier = None

    if "sekitar" in lower:
        qualifier = TimelineQualifier.SEKITAR.value
    elif "diperkirakan" in lower:
        qualifier = TimelineQualifier.DIPERKIRAKAN.value
    elif "sebelum" in lower:
        qualifier = TimelineQualifier.SEBELUM.value
    elif "dilaporkan pada" in lower or "dilaporkan" in lower:
        qualifier = TimelineQualifier.DILAPORKAN_PADA.value
    elif "tepat" in lower:
        qualifier = TimelineQualifier.TEPAT.value

    return qualifier, text


def normalize_to_utc(
    raw_time: str | None,
    qualifier: str | None = None,
    source_timezone: str | None = None,
    published_time: datetime | str | None = None,
) -> tuple[datetime | None, str | None, TimelinePrecision]:
    """Normalize raw event time to UTC ISO-8601 while retaining qualifiers and precision.

    Returns:
        (utc_datetime, canonical_qualifier, precision)
    """
    if not raw_time or not str(raw_time).strip():
        return None, qualifier, TimelinePrecision.UNKNOWN

    raw_str = str(raw_time).strip()
    detected_qualifier, clean_raw = extract_qualifier(raw_str)
    final_qualifier = qualifier or detected_qualifier

    ref_dt = parse_datetime_flexible(published_time)
    if ref_dt is None:
        ref_dt = datetime.now(JAKARTA_TZ)

    # 1. Check for Range
    if "antara" in clean_raw.lower() or " - " in clean_raw or " s/d " in clean_raw:
        # Range precision
        # Parse first time in range if possible
        time_m = re.search(r"(\d{1,2})[:.](\d{2})", clean_raw)
        if time_m:
            hour, minute = int(time_m.group(1)), int(time_m.group(2))
            dt = ref_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return dt.astimezone(UTC_TZ), final_qualifier, TimelinePrecision.RANGE
        return None, final_qualifier, TimelinePrecision.RANGE

    # 2. Check for explicit ISO format
    try:
        iso_dt = datetime.fromisoformat(clean_raw)
        if iso_dt.tzinfo is None:
            iso_dt = iso_dt.replace(tzinfo=JAKARTA_TZ)
        prec = (
            TimelinePrecision.APPROXIMATE
            if final_qualifier
            else TimelinePrecision.EXACT
        )
        return iso_dt.astimezone(UTC_TZ), final_qualifier, prec
    except ValueError:
        pass

    # 3. Check for Indonesian date: "10 Oktober 2026" or "10 Okt 2026"
    date_match = re.search(
        r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})(?:.*?(\d{1,2})[:.](\d{2}))?", clean_raw
    )
    if date_match:
        day = int(date_match.group(1))
        month_str = date_match.group(2).lower()
        year = int(date_match.group(3))
        month = MONTH_MAP_ID.get(month_str, ref_dt.month)
        hour = int(date_match.group(4)) if date_match.group(4) else 0
        minute = int(date_match.group(5)) if date_match.group(5) else 0

        tz = ZoneInfo(source_timezone) if source_timezone else JAKARTA_TZ
        dt = datetime(year, month, day, hour, minute, 0, tzinfo=tz)

        if date_match.group(4):
            prec = (
                TimelinePrecision.APPROXIMATE
                if final_qualifier
                else TimelinePrecision.EXACT
            )
        else:
            prec = TimelinePrecision.DAY

        return dt.astimezone(UTC_TZ), final_qualifier, prec

    # 4. Check for clock time with reference date: "pukul 09:30 WIB" or "09.30 WIB"
    clock_match = re.search(r"(?:pukul\s+)?(\d{1,2})[:.](\d{2})", clean_raw.lower())
    if clock_match:
        hour, minute = int(clock_match.group(1)), int(clock_match.group(2))
        tz = ZoneInfo(source_timezone) if source_timezone else JAKARTA_TZ
        ref_in_tz = ref_dt.astimezone(tz)
        dt = ref_in_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
        prec = (
            TimelinePrecision.APPROXIMATE
            if final_qualifier
            else TimelinePrecision.EXACT
        )
        return dt.astimezone(UTC_TZ), final_qualifier, prec

    # 5. Check relative time markers
    lower_raw = clean_raw.lower()
    if "dua jam setelah" in lower_raw or "2 jam setelah" in lower_raw:
        dt = ref_dt + timedelta(hours=2)
        return (
            dt.astimezone(UTC_TZ),
            final_qualifier or "sekitar",
            TimelinePrecision.APPROXIMATE,
        )

    if "kemarin pagi" in lower_raw or "kemarin" in lower_raw:
        dt = (ref_dt - timedelta(days=1)).replace(hour=8, minute=0, second=0)
        return (
            dt.astimezone(UTC_TZ),
            final_qualifier or "sekitar",
            TimelinePrecision.DAY,
        )

    if "siang ini" in lower_raw or "siang" in lower_raw:
        dt = ref_dt.replace(hour=12, minute=0, second=0)
        return (
            dt.astimezone(UTC_TZ),
            final_qualifier or "sekitar",
            TimelinePrecision.APPROXIMATE,
        )

    if "pagi" in lower_raw:
        dt = ref_dt.replace(hour=8, minute=0, second=0)
        return (
            dt.astimezone(UTC_TZ),
            final_qualifier or "sekitar",
            TimelinePrecision.APPROXIMATE,
        )

    # Unknown / unresolvable
    return None, final_qualifier, TimelinePrecision.UNKNOWN


def format_display_time(
    utc_dt: datetime | None,
    qualifier: str | None = None,
    precision: TimelinePrecision | str = TimelinePrecision.EXACT,
    tz_name: str = "Asia/Jakarta",
) -> str:
    """Format UTC datetime for UI display in Asia/Jakarta (WIB) with qualifier preserved.

    Authority: DEC-0001
    """
    if utc_dt is None:
        return "Waktu belum terkonfirmasi"

    tz = ZoneInfo(tz_name)
    local_dt = utc_dt.astimezone(tz)

    prec_str = str(precision).upper()
    prefix = f"{qualifier} " if qualifier else ""

    if "DAY" in prec_str:
        return f"{prefix}{local_dt.strftime('%d %b %Y')}".strip()

    time_str = local_dt.strftime("%d %b %Y, %H:%M WIB")
    return f"{prefix}{time_str}".strip()
