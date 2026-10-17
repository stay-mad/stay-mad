"""Unit tests for Ingestion and Source Allowlist Policy.

Authority: DEC-0003, docs/sources.md, config/sources.yaml
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.staymad.ingest.parser import (
    RawArticle,
    parse_rss_feed_xml,
    process_raw_article,
)
from backend.staymad.ingest.sources import (
    SourceRegistry,
    UnauthorizedSourceError,
)
from backend.staymad.normalize.text import compute_content_hash, create_excerpt


@pytest.fixture
def source_registry() -> SourceRegistry:
    return SourceRegistry.load_from_yaml()


def test_allowlist_permits_authorized_domains(source_registry: SourceRegistry):
    authorized = [
        "data.bmkg.go.id",
        "bpbd.jakarta.go.id",
        "bnpb.go.id",
        "setkab.go.id",
        "antaranews.com",
        "news.detik.com",
        "cnnindonesia.com",
        "republika.co.id",
        "tempo.co",
        "kompas.com",
        "cnbcindonesia.com",
    ]
    for domain in authorized:
        assert source_registry.is_domain_allowed(domain), (
            f"Domain '{domain}' should be allowed"
        )


def test_allowlist_rejects_unauthorized_domains(source_registry: SourceRegistry):
    unauthorized = [
        "randomblog.wordpress.com",
        "fakestuff.xyz",
        "unverifiednews.co.id",
        "evil-injector.com",
    ]
    for domain in unauthorized:
        assert not source_registry.is_domain_allowed(domain)
        with pytest.raises(UnauthorizedSourceError):
            source_registry.validate_article_source(domain)


def test_media_conglomerate_syndication_detection(source_registry: SourceRegistry):
    # Detikcom and CNN Indonesia both belong to TRANSMEDIA
    assert source_registry.is_same_source_family("news.detik.com", "cnnindonesia.com")
    assert source_registry.is_same_source_family(
        "cnnindonesia.com", "cnbcindonesia.com"
    )

    # BMKG and Detikcom do not belong to the same family
    assert not source_registry.is_same_source_family(
        "data.bmkg.go.id", "news.detik.com"
    )


def test_content_hashing_deduplication():
    title_1 = "Banjir Merendam Cipinang Melayu"
    content_1 = "Sebanyak lima kecamatan di Jakarta Timur terendam banjir akibat luapan Ciliwung."

    # Same content with minor whitespace differences should produce identical hash
    title_2 = "  Banjir Merendam Cipinang Melayu  "
    content_2 = "Sebanyak lima  kecamatan di Jakarta Timur terendam banjir akibat luapan Ciliwung.\n"

    hash_1 = compute_content_hash(title_1, content_1)
    hash_2 = compute_content_hash(title_2, content_2)
    assert hash_1 == hash_2, "Normalized content hash should match"

    # Different content should produce distinct hash
    content_3 = "Sebanyak tujuh kecamatan di Jakarta Timur terendam banjir."
    hash_3 = compute_content_hash(title_1, content_3)
    assert hash_1 != hash_3, "Differing content must produce distinct hash"


def test_retention_policy_calculation(source_registry: SourceRegistry):
    # LKBN ANTARA retention is 7 days, BPBD DKI is 30 days
    now = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
    raw_antara = RawArticle(
        url="https://www.antaranews.com/berita/123/uji",
        title="Uji Berita",
        content_text="Uji isi berita teks.",
        published_at="2026-10-10T10:00:00Z",
        source_domain="antaranews.com",
    )
    ingested_antara = process_raw_article(raw_antara, source_registry, fetch_time=now)
    assert ingested_antara.full_text_expires_at is not None
    assert (ingested_antara.full_text_expires_at - now).days == 7

    raw_bpbd = RawArticle(
        url="https://bpbd.jakarta.go.id/berita/456",
        title="Rilis BPBD",
        content_text="Rilis resmi BPBD DKI.",
        published_at="2026-10-10T10:00:00Z",
        source_domain="bpbd.jakarta.go.id",
    )
    ingested_bpbd = process_raw_article(raw_bpbd, source_registry, fetch_time=now)
    assert ingested_bpbd.full_text_expires_at is not None
    assert (ingested_bpbd.full_text_expires_at - now).days == 30


def test_excerpt_truncation_under_500_chars():
    long_text = "Kata " * 300  # ~1500 chars
    excerpt = create_excerpt(long_text, max_length=500)
    assert len(excerpt) <= 503  # with ellipsis


def test_rss_feed_parser(source_registry: SourceRegistry):
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Antara News Terkini</title>
        <link>https://www.antaranews.com</link>
        <description>Berita terkini Indonesia</description>
        <item>
          <title>Genangan di Jakarta Timur Mulai Surut</title>
          <link>https://www.antaranews.com/berita/999/genangan-surut</link>
          <description>Genangan air di sejumlah titik di Jakarta Timur berangsur surut pada Sabtu sore.</description>
          <pubDate>Sat, 10 Oct 2026 15:00:00 +0700</pubDate>
          <author>Redaksi Antara</author>
        </item>
      </channel>
    </rss>
    """
    items = parse_rss_feed_xml(sample_xml, "antaranews.com", source_registry)
    assert len(items) == 1
    item = items[0]
    assert item.title == "Genangan di Jakarta Timur Mulai Surut"
    assert "antaranews.com" in item.url
    assert item.source_config.source_family == "LKBN_ANTARA"
