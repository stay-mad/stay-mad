"""Article and RSS parser with deduplication content hashing and retention policy calculation.

Authority: docs/sources.md §3, docs/architecture/B-data-model.md §2.2–2.3
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from backend.staymad.db.models.enums import EventCategory
from backend.staymad.ingest.sources import SourceConfig, SourceRegistry
from backend.staymad.normalize.temporal import parse_datetime_flexible
from backend.staymad.normalize.text import (
    clean_text,
    compute_content_hash,
    create_excerpt,
)

UTC_TZ = UTC


class RawArticle(BaseModel):
    """Raw article data ingested from RSS, API, or fixture."""

    url: str
    title: str
    content_text: str
    published_at: str | datetime | None = None
    updated_at: str | datetime | None = None
    author: str | None = None
    category: str | None = None
    source_domain: str | None = None
    source_id: str | None = None
    edge_case_flags: list[str] = Field(default_factory=list)


class IngestedArticleVersion(BaseModel):
    """Normalized, deduplicated article payload ready for DB persistence & LLM extraction."""

    source_config: SourceConfig
    url: str
    title: str
    excerpt: str
    content_text: str
    author: str | None
    category_hint: EventCategory
    content_hash: str
    published_time: datetime | None
    updated_time: datetime | None
    fetch_time: datetime
    full_text_expires_at: datetime | None
    schema_version: str = "1.0"


def map_category_string(cat: str | None, text_fallback: str = "") -> EventCategory:
    """Map string category to EventCategory enum (bounded MVP per DEC-0002 & DEC-0007)."""
    norm_cat = (cat or "").strip().upper()
    norm_text = (text_fallback or "").strip().lower()

    # 1. Direct explicit category tag matching
    if norm_cat:
        if any(
            k in norm_cat
            for k in ("DISASTER", "WEATHER", "BANJIR", "MERAPI", "GEMPA", "CUACA")
        ):
            return EventCategory.DISASTER_AND_WEATHER
        if any(
            k in norm_cat
            for k in ("TRANSPORT", "KRL", "LALU LINTAS", "DISHUB", "KERETA", "OTOMOTIF")
        ):
            return EventCategory.TRANSPORTATION_AND_INFRASTRUCTURE
        if any(
            k in norm_cat
            for k in (
                "GOVERNMENT",
                "POLICY",
                "KEBIJAKAN",
                "PERPRES",
                "POLITIK",
                "HUKUM",
                "NASIONAL",
                "METRO",
                "KORUPSI",
            )
        ):
            return EventCategory.GOVERNMENT_AND_PUBLIC_POLICY

    # 2. Text fallback semantic keyword matching
    if norm_text:
        # Check transportation & infrastructure
        if any(
            k in norm_text
            for k in (
                "krl",
                "mrt",
                "lrt",
                "kereta",
                "commuter",
                "jalan tol",
                "kemacetan",
                "lalu lintas",
                "dishub",
                "transjakarta",
                "bandara",
                "pelabuhan",
                "pesawat",
                "penerbangan",
                "terminal",
                "jembatan",
                "infrastruktur",
                "jalur ganda",
                "stasiun",
            )
        ):
            return EventCategory.TRANSPORTATION_AND_INFRASTRUCTURE

        # Check disaster & weather
        if any(
            k in norm_text
            for k in (
                "banjir",
                "gempa",
                "merapi",
                "gunung api",
                "erupsi",
                "tsunami",
                "longsor",
                "karhutla",
                "kebakaran hutan",
                "cuaca ekstrem",
                "hujan lebat",
                "bnpb",
                "bpbd",
                "bmkg",
                "kekeringan",
                "angin kencang",
                "puting beliung",
                "rob",
            )
        ):
            return EventCategory.DISASTER_AND_WEATHER

        # Check government & public policy
        if any(
            k in norm_text
            for k in (
                "kpk",
                "korupsi",
                "ott",
                "bupati",
                "gubernur",
                "walikota",
                "presiden",
                "menteri",
                "dpr",
                "mpr",
                "mk",
                "mahkamah",
                "pemilu",
                "pilkada",
                "kebijakan",
                "perpres",
                "uu ",
                "undang-undang",
                "apbd",
                "apbn",
                "pemerintah",
                "kemenkeu",
                "kemendagri",
                "politik",
                "haji",
                "kemenag",
                "duta besar",
                "diplomasi",
                "tersangka",
                "vonis",
            )
        ):
            return EventCategory.GOVERNMENT_AND_PUBLIC_POLICY

    # Safe default: government & public policy for general urban governance news
    return EventCategory.GOVERNMENT_AND_PUBLIC_POLICY


def process_raw_article(
    raw: RawArticle | dict[str, Any],
    registry: SourceRegistry,
    fetch_time: datetime | None = None,
) -> IngestedArticleVersion:
    """Validate, clean, deduplicate, and compute retention for an incoming article."""
    if isinstance(raw, dict):
        raw_obj = RawArticle(**raw)
    else:
        raw_obj = raw

    # Validate against sources allowlist
    domain_to_check = raw_obj.source_domain or raw_obj.url
    source_cfg = registry.validate_article_source(domain_to_check)

    clean_title = clean_text(raw_obj.title)
    clean_body = clean_text(raw_obj.content_text)
    content_hash = compute_content_hash(clean_title, clean_body)
    excerpt = create_excerpt(clean_body or clean_title, max_length=500)

    now = fetch_time or datetime.now(UTC_TZ)
    published_dt = parse_datetime_flexible(raw_obj.published_at)
    if published_dt and published_dt.tzinfo is None:
        published_dt = published_dt.replace(tzinfo=UTC_TZ)
    elif published_dt:
        published_dt = published_dt.astimezone(UTC_TZ)

    updated_dt = parse_datetime_flexible(raw_obj.updated_at)
    if updated_dt and updated_dt.tzinfo is None:
        updated_dt = updated_dt.replace(tzinfo=UTC_TZ)
    elif updated_dt:
        updated_dt = updated_dt.astimezone(UTC_TZ)

    # Compute retention expiry per docs/sources.md
    retention_days = source_cfg.retention_days_full_text or 7
    expires_at = now + timedelta(days=retention_days)

    cat_enum = map_category_string(raw_obj.category, f"{clean_title} {clean_body}")

    return IngestedArticleVersion(
        source_config=source_cfg,
        url=raw_obj.url.strip(),
        title=clean_title,
        excerpt=excerpt,
        content_text=clean_body,
        author=raw_obj.author.strip() if raw_obj.author else None,
        category_hint=cat_enum,
        content_hash=content_hash,
        published_time=published_dt,
        updated_time=updated_dt,
        fetch_time=now,
        full_text_expires_at=expires_at,
        schema_version="1.0",
    )


def _clean_xml_cdata_or_text(val: str) -> str:
    """Strip CDATA wrapping or HTML entities."""
    val = val.strip()
    if val.startswith("<![CDATA[") and val.endswith("]]>"):
        val = val[9:-3].strip()
    return val


def parse_rss_feed_xml(
    xml_content: str, source_domain: str, registry: SourceRegistry
) -> list[IngestedArticleVersion]:
    """Parse standard RSS 2.0 XML string into list of IngestedArticleVersion items."""
    source_cfg = registry.validate_article_source(source_domain)
    now = datetime.now(UTC_TZ)
    results = []

    # Sanitize naked ampersands that break XML parsing
    sanitized_xml = re.sub(
        r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)", "&amp;", xml_content
    )

    try:
        root = ET.fromstring(sanitized_xml)
        channel = root.find("channel")
        if channel is None:
            channel = root

        items = channel.findall("item")
        for it in items:
            title = it.findtext("title") or ""
            link = it.findtext("link") or ""
            desc = it.findtext("description") or ""
            pub_date = it.findtext("pubDate") or ""
            category = it.findtext("category") or ""
            author = it.findtext("author") or it.findtext(
                "dc:creator", namespaces={"dc": "http://purl.org/dc/elements/1.1/"}
            )

            if not link or not title:
                continue

            raw = RawArticle(
                url=link.strip(),
                title=title.strip(),
                content_text=desc.strip(),
                published_at=pub_date.strip() if pub_date else None,
                author=author.strip() if author else None,
                category=category.strip() if category else None,
                source_domain=source_domain,
                source_id=source_cfg.id,
            )
            results.append(process_raw_article(raw, registry, fetch_time=now))
        return results
    except ET.ParseError:
        # Fallback: regex extraction of item blocks if live XML stream has malformed/truncated tokens
        item_blocks = re.findall(
            r"<item\b[^>]*>(.*?)</item>", xml_content, re.DOTALL | re.IGNORECASE
        )
        for block in item_blocks:
            t_match = re.search(
                r"<title\b[^>]*>(.*?)</title>", block, re.DOTALL | re.IGNORECASE
            )
            l_match = re.search(
                r"<link\b[^>]*>(.*?)</link>", block, re.DOTALL | re.IGNORECASE
            )
            d_match = re.search(
                r"<description\b[^>]*>(.*?)</description>",
                block,
                re.DOTALL | re.IGNORECASE,
            )
            p_match = re.search(
                r"<pubDate\b[^>]*>(.*?)</pubDate>", block, re.DOTALL | re.IGNORECASE
            )
            c_match = re.search(
                r"<category\b[^>]*>(.*?)</category>", block, re.DOTALL | re.IGNORECASE
            )
            a_match = re.search(
                r"<(?:author|dc:creator)\b[^>]*>(.*?)</(?:author|dc:creator)>",
                block,
                re.DOTALL | re.IGNORECASE,
            )

            title = _clean_xml_cdata_or_text(t_match.group(1)) if t_match else ""
            link = _clean_xml_cdata_or_text(l_match.group(1)) if l_match else ""
            desc = _clean_xml_cdata_or_text(d_match.group(1)) if d_match else ""
            pub_date = _clean_xml_cdata_or_text(p_match.group(1)) if p_match else None
            category = _clean_xml_cdata_or_text(c_match.group(1)) if c_match else None
            author = _clean_xml_cdata_or_text(a_match.group(1)) if a_match else None

            if not link or not title:
                continue

            raw = RawArticle(
                url=link.strip(),
                title=title.strip(),
                content_text=desc.strip(),
                published_at=pub_date.strip() if pub_date else None,
                author=author.strip() if author else None,
                category=category.strip() if category else None,
                source_domain=source_domain,
                source_id=source_cfg.id,
            )
            results.append(process_raw_article(raw, registry, fetch_time=now))
        return results
