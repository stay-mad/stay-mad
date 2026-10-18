"""Live RSS Ingestion Pipeline Runner for Stay Mad.

Fetches real-time RSS news feeds from authorized sources (LKBN Antara),
extracts grounded factual claims via Google Gemini API,
resolves canonical events, and persists them into PostgreSQL with DATA_MODE=LIVE.

Authority: DEC-0003, DEC-0005, DEC-0006
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from backend.staymad.db.base import Base
from backend.staymad.db.session import create_db_engine, create_session_factory
from backend.staymad.events.manager import EventSynthesisManager
from backend.staymad.ingest.parser import parse_rss_feed_xml
from backend.staymad.ingest.pipeline import IngestExtractionPipeline
from backend.staymad.ingest.sources import SourceRegistry
from backend.staymad.llm.factory import get_llm_client
from backend.staymad.resolver.manager import EventResolverManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("staymad.live_ingest")

KNOWN_RSS_SOURCES: dict[str, dict[str, Any]] = {
    "antara": {
        "name": "LKBN Antara",
        "domain": "antaranews.com",
        "url": "https://www.antaranews.com/rss/terkini.xml",
        "fallbacks": ["https://www.antaranews.com/rss/top-news.xml"],
    },
    "cnn": {
        "name": "CNN Indonesia",
        "domain": "cnnindonesia.com",
        "url": "https://www.cnnindonesia.com/nasional/rss",
        "fallbacks": [],
    },
    "detik": {
        "name": "Detikcom",
        "domain": "news.detik.com",
        "url": "https://news.detik.com/berita/rss",
        "fallbacks": [],
    },
    "tempo": {
        "name": "Tempo.co",
        "domain": "tempo.co",
        "url": "https://rss.tempo.co/nasional",
        "fallbacks": [],
    },
    "republika": {
        "name": "Republika",
        "domain": "republika.co.id",
        "url": "https://republika.co.id/rss",
        "fallbacks": [],
    },
    "cnbc": {
        "name": "CNBC Indonesia",
        "domain": "cnbcindonesia.com",
        "url": "https://www.cnbcindonesia.com/news/rss",
        "fallbacks": [],
    },
    "setkab": {
        "name": "Sekretariat Kabinet RI",
        "domain": "setkab.go.id",
        "url": "https://setkab.go.id/feed",
        "fallbacks": [],
    },
}

DEFAULT_RSS_URL = KNOWN_RSS_SOURCES["antara"]["url"]
DEFAULT_DOMAIN = KNOWN_RSS_SOURCES["antara"]["domain"]


def _fetch_rss_content(url: str, fallbacks: list[str]) -> str | None:
    if "setkab.go.id" in url:
        headers = {"User-Agent": "Mozilla/5.0"}
    else:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    candidate_urls = [url, *fallbacks]
    for target_fetch_url in candidate_urls:
        for attempt in range(1, 4):
            try:
                with httpx.Client(
                    timeout=45.0, headers=headers, follow_redirects=True
                ) as client:
                    resp = client.get(target_fetch_url)
                    resp.raise_for_status()
                    return resp.text
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Percobaan %d mengambil %s gagal: %s",
                    attempt,
                    target_fetch_url,
                    e,
                )
                time.sleep(2)
    return None


def _fetch_bmkg_articles(limit: int = 3) -> list[dict[str, Any]]:
    """Fetch live earthquake telemetry directly from BMKG Open Data API."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9",
    }
    articles: list[dict[str, Any]] = []

    # 1. autogempa (gempa terbaru berpotensi dirasakan)
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            r = client.get("https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json")
            if r.status_code == 200:
                g = r.json().get("Infogempa", {}).get("gempa", {})
                if g:
                    title = f"BMKG: Gempa Magnitudo {g.get('Magnitude')} di {g.get('Wilayah')}"
                    body = (
                        f"Pusat gempa berada pada koordinat {g.get('Coordinates')}, kedalaman {g.get('Kedalaman')}. "
                        f"Dirasakan: {g.get('Dirasakan', '-')}. Potensi: {g.get('Potensi')}."
                    )
                    shakemap = g.get("Shakemap")
                    bmkg_url = (
                        f"https://data.bmkg.go.id/DataMKG/TEWS/{shakemap}"
                        if shakemap
                        else "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
                    )
                    articles.append(
                        {
                            "id": f"art_bmkg_auto_{int(time.time())}",
                            "title": title,
                            "url": bmkg_url,
                            "published_at": g.get("DateTime")
                            or datetime.now().isoformat(),
                            "source_domain": "data.bmkg.go.id",
                            "source_id": "src_bmkg_data",
                            "content_text": body,
                            "author": "BMKG",
                        }
                    )
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil autogempa BMKG: %s", e)

    # 2. gempaterkini (daftar 15 gempa terakhir)
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            r = client.get("https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json")
            if r.status_code == 200:
                gempa_list = r.json().get("Infogempa", {}).get("gempa", [])
                for idx, g in enumerate(gempa_list):
                    if len(articles) >= limit:
                        break
                    title = f"BMKG: Gempa M {g.get('Magnitude')} {g.get('Tanggal')} di {g.get('Wilayah')}"
                    body = (
                        f"BMKG mencatat gempa bumi magnitudo {g.get('Magnitude')} pada {g.get('Tanggal')} pukul {g.get('Jam')}. "
                        f"Lokasi koordinat {g.get('Coordinates')}, kedalaman {g.get('Kedalaman')}, wilayah {g.get('Wilayah')}."
                    )
                    articles.append(
                        {
                            "id": f"art_bmkg_list_{int(time.time())}_{idx}",
                            "title": title,
                            "url": "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json",
                            "published_at": g.get("DateTime")
                            or datetime.now().isoformat(),
                            "source_domain": "data.bmkg.go.id",
                            "source_id": "src_bmkg_data",
                            "content_text": body,
                            "author": "BMKG",
                        }
                    )
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil gempaterkini BMKG: %s", e)

    return articles[:limit]


def _fetch_bpbd_articles(limit: int = 3) -> list[dict[str, Any]]:
    """Fetch live emergency updates from BPBD DKI Jakarta."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9",
    }
    articles: list[dict[str, Any]] = []
    try:
        with httpx.Client(
            timeout=15.0, headers=headers, follow_redirects=True
        ) as client:
            r = client.get("https://bpbd.jakarta.go.id/berita")
            if r.status_code == 200:
                matches = re.findall(
                    r'<a[^>]+href="(https://bpbd\.jakarta\.go\.id/berita/[^"]+)"[^>]*>(.*?)</a>',
                    r.text,
                    re.DOTALL,
                )
                seen_urls = set()
                now_iso = datetime.now().isoformat()
                for url, raw_text in matches:
                    clean_title = re.sub(r"<[^>]+>", "", raw_text).strip()
                    if clean_title and len(clean_title) > 20 and url not in seen_urls:
                        seen_urls.add(url)
                        articles.append(
                            {
                                "id": f"art_bpbd_{int(time.time())}_{len(articles)}",
                                "title": clean_title,
                                "url": url,
                                "published_at": now_iso,
                                "source_domain": "bpbd.jakarta.go.id",
                                "source_id": "src_bpbd_dki",
                                "content_text": f"BPBD DKI Jakarta melaporkan kegiatan kebencanaan dan penanganan: {clean_title}.",
                                "author": "BPBD DKI Jakarta",
                            }
                        )
                        if len(articles) >= limit:
                            break
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil berita BPBD DKI: %s", e)
    return articles


def _fetch_kompas_articles(limit: int = 3) -> list[dict[str, Any]]:
    """Fetch live news articles directly from Kompas.com (nasional)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9",
    }
    articles: list[dict[str, Any]] = []
    try:
        with httpx.Client(
            timeout=15.0, headers=headers, follow_redirects=True
        ) as client:
            r = client.get("https://nasional.kompas.com")
            if r.status_code == 200:
                matches = re.findall(
                    r"<a[^>]+href=[\"\x27](https://[^\s\"\x27]*kompas\.com/read/[^\s\"\x27]+)[\"\x27][^>]*>(.*?)</a>",
                    r.text,
                    re.DOTALL,
                )
                seen_urls = set()
                now_iso = datetime.now().isoformat()
                for url, raw_text in matches:
                    clean_title = re.sub(r"<[^>]+>", "", raw_text).strip()
                    clean_title = re.sub(r"\s+", " ", clean_title)
                    clean_title = re.sub(r"^\d+\s+", "", clean_title)
                    clean_title = re.sub(
                        r"\s+[A-Za-z]+\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}$", "", clean_title
                    )
                    if clean_title and len(clean_title) > 20 and url not in seen_urls:
                        seen_urls.add(url)
                        articles.append(
                            {
                                "id": f"art_kompas_{int(time.time())}_{len(articles)}",
                                "title": clean_title,
                                "url": url,
                                "published_at": now_iso,
                                "source_domain": "kompas.com",
                                "source_id": "src_kompas",
                                "content_text": f"Kompas.com melaporkan peristiwa nasional: {clean_title}.",
                                "author": "Kompas.com",
                            }
                        )
                        if len(articles) >= limit:
                            break
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil berita Kompas: %s", e)
    return articles


def run_live_ingest(
    source: str = "antara",
    rss_url: str | None = None,
    domain: str | None = None,
    max_articles: int = 3,
    db_url: str | None = None,
) -> None:
    print("=" * 60)
    print(" Stay Mad — Live News Ingestion Runner")
    print("=" * 60)

    # 1. Pastikan environment live aktif & load .env jika ada
    os.environ["DATA_MODE"] = "live"

    if Path(".env").exists():
        with open(".env", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    if not os.getenv(k):
                        os.environ[k] = v

    target_url = db_url or os.getenv("DATABASE_URL")
    if not target_url:
        target_url = "postgresql://staymad:staymad_secret@localhost:5432/staymad_db"

    print(
        f"🗄  Koneksi Database: {target_url.split('@')[-1] if '@' in target_url else target_url}"
    )

    registry = SourceRegistry.load_from_yaml()
    raw_articles: list[dict[str, Any]] = []
    now_iso = datetime.now().isoformat()

    s_key = source.strip().lower()

    # Periksa sumber khusus non-RSS (BMKG API dan BPBD DKI)
    if s_key in ("bmkg", "data.bmkg.go.id", "src_bmkg_data"):
        print(
            "📡 Mengambil data terbuka langsung dari API BMKG (autogempa & gempaterkini)..."
        )
        raw_articles = _fetch_bmkg_articles(limit=max_articles)
    elif s_key in ("bpbd", "bpbd_dki", "bpbd.jakarta.go.id", "src_bpbd_dki"):
        print(
            "📡 Mengambil laporan kebencanaan resmi langsung dari BPBD DKI Jakarta..."
        )
        raw_articles = _fetch_bpbd_articles(limit=max_articles)
    elif s_key in ("kompas", "kompas.com", "src_kompas"):
        print("📡 Mengambil berita nasional langsung dari Kompas.com...")
        raw_articles = _fetch_kompas_articles(limit=max_articles)
    elif s_key in ("bnpb", "bnpb.go.id", "src_bnpb"):
        print(
            "⚠️  Portal BNPB (bnpb.go.id) saat ini diproteksi oleh Cloudflare Bot Challenge (HTTP 403 Forbidden).",
            file=sys.stderr,
        )
        print(
            "💡 Disarankan menggunakan 'bmkg' (API Terbuka Data Gempa/Cuaca) atau 'bpbd' (Laporan Kebencanaan DKI) untuk data resmi Tier 1.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif s_key in ("tier1", "gov"):
        print(
            "🏛️ Mengambil dari SEMUA sumber Tier 1 Resmi (BMKG, BPBD DKI, Setkab, Antara)..."
        )
        bmkg_items = _fetch_bmkg_articles(limit=1)
        bpbd_items = _fetch_bpbd_articles(limit=1)
        raw_articles.extend(bmkg_items)
        raw_articles.extend(bpbd_items)
        # Ambil Setkab dan Antara lewat RSS
        for gov_key in ("setkab", "antara"):
            info = KNOWN_RSS_SOURCES[gov_key]
            xml = _fetch_rss_content(info["url"], info["fallbacks"])
            if xml:
                try:
                    parsed = parse_rss_feed_xml(xml, info["domain"], registry)
                    if parsed:
                        it = parsed[0]
                        raw_articles.append(
                            {
                                "id": f"art_live_{int(time.time())}_{len(raw_articles)}",
                                "title": it.title,
                                "url": it.url,
                                "published_at": it.published_time.isoformat()
                                if it.published_time
                                else now_iso,
                                "source_domain": info["domain"],
                                "source_id": it.source_config.id,
                                "content_text": it.content_text
                                or it.excerpt
                                or it.title,
                                "author": it.author,
                            }
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning("Gagal parse feed %s: %s", gov_key, e)
    else:
        # Sumber RSS standar
        for k, v in KNOWN_RSS_SOURCES.items():
            if s_key in (k, v["domain"], f"src_{k}") or s_key in v["domain"]:
                s_key = k
                break

        targets: list[tuple[str, str, list[str]]] = []
        if rss_url and domain:
            targets.append((domain, rss_url, []))
            print(f"📡 Mengambil custom feed: {rss_url} ({domain})")
        elif s_key == "all":
            print(
                f"🌐 Mengambil dari SEMUA portal berita resmi ({', '.join(KNOWN_RSS_SOURCES.keys())})"
            )
            for s_info in KNOWN_RSS_SOURCES.values():
                targets.append((s_info["domain"], s_info["url"], s_info["fallbacks"]))
        elif s_key in KNOWN_RSS_SOURCES:
            s_info = KNOWN_RSS_SOURCES[s_key]
            targets.append((s_info["domain"], s_info["url"], s_info["fallbacks"]))
            print(f"📡 Mengambil feed portal: {s_info['name']} ({s_info['domain']})")
        else:
            available = list(KNOWN_RSS_SOURCES.keys()) + [
                "kompas",
                "bmkg",
                "bpbd",
                "tier1",
            ]
            print(
                f"❌ Sumber '{source}' tidak dikenal. Pilihan yang tersedia: {available} atau 'all'",
                file=sys.stderr,
            )
            sys.exit(1)

        for s_domain, s_url, s_fallbacks in targets:
            xml_content = _fetch_rss_content(s_url, s_fallbacks)
            if not xml_content:
                logger.warning(
                    "Gagal mengambil feed dari %s, melewati sumber ini.", s_url
                )
                continue
            try:
                parsed = parse_rss_feed_xml(xml_content, s_domain, registry)
                per_source_quota = max(1, (max_articles + len(targets) - 1) // len(targets)) if s_key == "all" else max_articles
                selected = parsed[:per_source_quota]
                for idx, item in enumerate(selected):
                    raw_articles.append(
                        {
                            "id": f"art_live_{int(time.time())}_{len(raw_articles)}_{idx}",
                            "title": item.title,
                            "url": item.url,
                            "published_at": (
                                item.published_time.isoformat()
                                if item.published_time
                                else now_iso
                            ),
                            "source_domain": s_domain,
                            "source_id": item.source_config.id,
                            "content_text": item.content_text
                            or item.excerpt
                            or item.title,
                            "author": item.author,
                        }
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("Gagal memproses feed %s: %s", s_domain, e)

    if not raw_articles:
        print("❌ Tidak ada artikel yang berhasil diambil dari feed.", file=sys.stderr)
        sys.exit(1)

    # Batasi ke max_articles
    raw_articles = raw_articles[:max_articles]
    print(f"\n📰 Berhasil mengumpulkan {len(raw_articles)} artikel berita terkini:")
    for idx, it in enumerate(raw_articles, 1):
        print(f"  [{idx}] ({it['source_domain']}) {it['title'][:65]}...")

    # 4. Inisialisasi Database Engine & Session
    engine = create_db_engine(target_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    # 5. Siapkan LLM Client (Gemini Live)
    print("\n🤖 Menginisialisasi Gemini LLM Client...")
    try:
        llm = get_llm_client(data_mode="LIVE", use_mock=False)
        print(f"✓ LLM Client siap menggunakan model: {llm.model_version}")
    except Exception as e:  # noqa: BLE001
        print(
            f"❌ Inisialisasi LLM gagal (periksa GEMINI_API_KEY): {e}", file=sys.stderr
        )
        sys.exit(1)

    pipeline = IngestExtractionPipeline(registry=registry, llm_client=llm)

    with session_factory() as session:
        print("\n⚙️  Menjalankan ekstraksi klaim berbasis bukti...")
        try:
            result = pipeline.process_batch(raw_articles, session)
        except Exception as e:  # noqa: BLE001
            print(f"❌ Kesalahan pada tahap ekstraksi: {e}", file=sys.stderr)
            session.rollback()
            sys.exit(1)

        print("✓ Ekstraksi Berhasil:")
        print(f"  - Artikel Tersimpan: {result.articles_saved}")
        print(f"  - Klaim Terverifikasi: {result.claims_extracted}")
        print(f"  - Klaim Digugurkan (Tanpa Bukti): {result.claims_gated_out}")

        # 6. Event Resolution
        print("\n🧩 Mengelompokkan berita ke dalam Canonical Events...")
        resolver = EventResolverManager(
            session=session, llm_client=llm, ablation_mode="tier3"
        )
        touched_event_ids: set[uuid.UUID] = set()
        for art_ver in result.article_versions:
            ver_claims = [
                c for c in result.claims if c.article_version_id == art_ver.id
            ]
            res = resolver.resolve_article_version(
                art_ver, ver_claims, result.processing_run_id
            )
            if res and res.event_id:
                touched_event_ids.add(res.event_id)
        session.commit()
        print(
            f"✓ Resolusi Selesai: {len(touched_event_ids)} event kanonikal diperbarui/terbentuk."
        )

        # 7. Synthesis & Snapshots
        print("\n📊 Menyusun Event Snapshots & Linimasa WIB...")
        synth_mgr = EventSynthesisManager(session=session, llm_client=llm)
        created_count = 0
        for ev_id in touched_event_ids:
            snap = synth_mgr.synthesize_event_snapshot(
                event_id=ev_id,
                processing_run_id=result.processing_run_id,
                force_snapshot=True,
            )
            if snap:
                created_count += 1
                print(
                    f"  - [{snap.actionability_level.value}] {snap.headline[:50]}... "
                    f"(Keyakinan: {snap.confidence_score:.0%})"
                )

        session.commit()
        print(
            f"\n🎉 SELESAI! {created_count} peristiwa berhasil dipublikasikan ke tab LIVE."
        )
        print(
            "👉 Silakan buka http://localhost:3000 dan pilih tab 'Live' untuk melihat hasilnya.\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stay Mad Live News Ingestion Runner")
    parser.add_argument(
        "--source",
        type=str,
        default="antara",
        help=f"Source key ({', '.join(KNOWN_RSS_SOURCES.keys())}, or 'all')",
    )
    parser.add_argument(
        "--rss-url",
        type=str,
        default=None,
        help="Custom RSS Feed URL (overrides --source)",
    )
    parser.add_argument(
        "--domain", type=str, default=None, help="Custom Authorized domain"
    )
    parser.add_argument("--limit", type=int, default=3, help="Max articles to process")
    parser.add_argument(
        "--db-url", type=str, default=None, help="Database connection URL"
    )
    args = parser.parse_args()

    run_live_ingest(
        source=args.source,
        rss_url=args.rss_url,
        domain=args.domain,
        max_articles=args.limit,
        db_url=args.db_url,
    )
