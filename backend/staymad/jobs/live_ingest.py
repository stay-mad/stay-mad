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

ORDERED_ALLOWLIST_FEEDS: list[str] = [
    "antara",
    "tempo",
    "cnbc",
    "detik",
    "cnn",
    "setkab",
]

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
        for attempt in range(1, 3):
            try:
                with httpx.Client(
                    timeout=15.0, headers=headers, follow_redirects=True
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
                time.sleep(1)
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
                            "url": f"https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json#{idx}",
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


def execute_live_ingest_cycle(
    source: str = "antara",
    rss_url: str | None = None,
    domain: str | None = None,
    max_articles: int = 3,
    db_url: str | None = None,
    last_run_cutoff: datetime | None = None,
) -> tuple[dict[str, Any], datetime | None]:
    """Execute one batch ingestion, extraction, resolution, and synthesis cycle.

    Enforces DEC-0003, DEC-0004, DEC-0006 with database deduplication check.
    """
    orig_data_mode = os.environ.get("DATA_MODE")
    os.environ["DATA_MODE"] = "live"
    try:
        return _execute_live_ingest_cycle_impl(
            source=source,
            rss_url=rss_url,
            domain=domain,
            max_articles=max_articles,
            db_url=db_url,
            last_run_cutoff=last_run_cutoff,
        )
    finally:
        if orig_data_mode is None:
            os.environ.pop("DATA_MODE", None)
        else:
            os.environ["DATA_MODE"] = orig_data_mode


def _execute_live_ingest_cycle_impl(
    source: str = "antara",
    rss_url: str | None = None,
    domain: str | None = None,
    max_articles: int = 3,
    db_url: str | None = None,
    last_run_cutoff: datetime | None = None,
) -> tuple[dict[str, Any], datetime | None]:
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
        target_url = "sqlite:///backend/staymad_dev.db"

    display_db = target_url.split("@")[-1] if "@" in target_url else target_url
    print(f"🗄  Koneksi Database: {display_db}")

    registry = SourceRegistry.load_from_yaml()
    raw_articles: list[dict[str, Any]] = []
    now_iso = datetime.now().isoformat()
    s_key = source.strip().lower()

    # 1. Fetching raw candidate articles
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
        logger.warning(
            "Portal BNPB (bnpb.go.id) terproteksi Cloudflare. Melewati sumber ini."
        )
    elif s_key in ("tier1", "gov"):
        print(
            "🏛️ Mengambil dari SEMUA sumber Tier 1 Resmi (BMKG, BPBD DKI, Setkab, Antara)..."
        )
        raw_articles.extend(_fetch_bmkg_articles(limit=1))
        raw_articles.extend(_fetch_bpbd_articles(limit=1))
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
                                "content_hash": it.content_hash,
                            }
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning("Gagal parse feed %s: %s", gov_key, e)
    else:
        # Standard RSS sources or 'all'
        targets: list[tuple[str, str, str, list[str]]] = []
        if rss_url and domain:
            targets.append(("custom", domain, rss_url, []))
            print(f"📡 Mengambil custom feed: {rss_url} ({domain})")
        elif s_key == "all":
            print(
                f"🌐 Polling berurutan ke seluruh feed resmi aktif di config/sources.yaml ({', '.join(ORDERED_ALLOWLIST_FEEDS)})"
            )
            for feed_k in ORDERED_ALLOWLIST_FEEDS:
                if feed_k in KNOWN_RSS_SOURCES:
                    s_info = KNOWN_RSS_SOURCES[feed_k]
                    targets.append(
                        (feed_k, s_info["domain"], s_info["url"], s_info["fallbacks"])
                    )
        elif s_key in KNOWN_RSS_SOURCES:
            s_info = KNOWN_RSS_SOURCES[s_key]
            targets.append(
                (s_key, s_info["domain"], s_info["url"], s_info["fallbacks"])
            )
            print(f"📡 Mengambil feed portal: {s_info['name']} ({s_info['domain']})")
        else:
            available = list(KNOWN_RSS_SOURCES.keys()) + [
                "kompas",
                "bmkg",
                "bpbd",
                "tier1",
            ]
            logger.error(
                "Sumber '%s' tidak dikenal. Pilihan: %s atau 'all'", source, available
            )
            return {
                "status": "error",
                "error_message": f"Sumber '{source}' tidak dikenal.",
                "total_found": 0,
                "new_articles_count": 0,
            }, last_run_cutoff

        for feed_name, s_domain, s_url, s_fallbacks in targets:
            print(f"  -> Mengambil feed {feed_name.upper()} ({s_url})...")
            xml_content = _fetch_rss_content(s_url, s_fallbacks)
            if not xml_content:
                logger.warning(
                    "⚠️  Feed %s (%s) offline/timeout. Melanjutkan ke sumber berikutnya.",
                    feed_name,
                    s_url,
                )
                continue
            try:
                parsed = parse_rss_feed_xml(xml_content, s_domain, registry)
                # Ambil hingga max_articles per sumber
                selected = parsed[:max_articles]
                print(
                    f"     ✓ {len(selected)} artikel ditemukan di feed {feed_name.upper()}."
                )
                for idx, item in enumerate(selected):
                    raw_articles.append(
                        {
                            "id": f"art_live_{int(time.time())}_{len(raw_articles)}_{idx}",
                            "title": item.title,
                            "url": item.url,
                            "published_at": item.published_time.isoformat()
                            if item.published_time
                            else now_iso,
                            "source_domain": s_domain,
                            "source_id": item.source_config.id,
                            "content_text": item.content_text
                            or item.excerpt
                            or item.title,
                            "author": item.author,
                            "content_hash": item.content_hash,
                        }
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("Gagal memproses feed %s: %s", s_domain, e)

    if not raw_articles:
        print("⚠️  Tidak ada artikel yang berhasil diambil dari feed pada siklus ini.")
        return {
            "status": "no_articles_fetched",
            "total_found": 0,
            "new_articles_count": 0,
            "claims_extracted": 0,
            "events_updated": 0,
        }, last_run_cutoff

    # Pastikan setiap artikel memiliki content_hash yang terisi
    from backend.staymad.db.models.article import Article, ArticleVersion
    from backend.staymad.ingest.parser import clean_text, compute_content_hash

    for it in raw_articles:
        if not it.get("content_hash"):
            c_title = clean_text(it.get("title", ""))
            c_body = clean_text(it.get("content_text", ""))
            it["content_hash"] = compute_content_hash(c_title, c_body)

    # 2. Database Deduplication & Filtering
    engine = create_db_engine(target_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    new_articles: list[dict[str, Any]] = []
    skipped_duplicate_count = 0
    skipped_older_count = 0
    latest_discovered_pub_time: datetime | None = None

    with session_factory() as session:
        # Load existing URLs and content_hashes from DB
        try:
            from sqlalchemy import select

            existing_rows = session.execute(
                select(Article.url, Article.content_hash)
            ).all()
            existing_urls = {row[0] for row in existing_rows if row[0]}
            existing_urls.update(
                {row[0].rstrip("/") for row in existing_rows if row[0]}
            )
            existing_hashes = {row[1] for row in existing_rows if row[1]}

            v_hashes = session.scalars(select(ArticleVersion.content_hash)).all()
            existing_hashes.update({h for h in v_hashes if h})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal memuat existing articles untuk deduplikasi: %s", exc)
            existing_urls = set()
            existing_hashes = set()

        for art in raw_articles:
            art_url = art.get("url", "").strip()
            art_url_norm = art_url.rstrip("/")
            art_hash = art.get("content_hash", "")
            pub_iso = art.get("published_at")

            # Check track of newest publication time
            if pub_iso:
                try:
                    p_dt = datetime.fromisoformat(pub_iso)
                    if (
                        latest_discovered_pub_time is None
                        or p_dt > latest_discovered_pub_time
                    ):
                        latest_discovered_pub_time = p_dt
                except (ValueError, TypeError):
                    pass

            # 2a. Deduplication check against DB
            if (
                art_url and (art_url in existing_urls or art_url_norm in existing_urls)
            ) or (art_hash and art_hash in existing_hashes):
                logger.info(
                    "⏩ [Dilewati - Duplikat DB] (%s) %s...",
                    art.get("source_domain"),
                    art.get("title", "")[:55],
                )
                skipped_duplicate_count += 1
                continue

            # 2b. Cutoff check since last run
            if last_run_cutoff and pub_iso:
                try:
                    p_dt = datetime.fromisoformat(pub_iso)
                    p_dt_utc = p_dt.astimezone() if p_dt.tzinfo else p_dt
                    cutoff_cmp = (
                        last_run_cutoff.astimezone()
                        if last_run_cutoff.tzinfo
                        else last_run_cutoff
                    )
                    if p_dt_utc <= cutoff_cmp:
                        logger.info(
                            "⏩ [Dilewati - Terbit sebelum run sebelumnya] (%s) %s...",
                            art.get("source_domain"),
                            art.get("title", "")[:55],
                        )
                        skipped_older_count += 1
                        continue
                except (ValueError, TypeError):
                    pass

            new_articles.append(art)

    print(
        f"\n🔍 Hasil Pemeriksaan Deduplikasi:"
        f"\n   - Total artikel di feed : {len(raw_articles)}"
        f"\n   - Duplikat dilewati     : {skipped_duplicate_count}"
        f"\n   - Berita lama dilewati  : {skipped_older_count}"
        f"\n   - Berita baru diproses  : {len(new_articles)}"
    )

    # If no new articles, skip Gemini LLM completely!
    if not new_articles:
        print("✓ Seluruh berita sudah tercatat di database.")
        print(
            "💡 Pemanggilan Gemini API dilewati — 0 token terpakai (menghemat kuota & biaya).\n"
        )
        return {
            "status": "no_new_articles",
            "total_found": len(raw_articles),
            "new_articles_count": 0,
            "skipped_duplicates": skipped_duplicate_count,
            "skipped_older": skipped_older_count,
            "claims_extracted": 0,
            "events_updated": 0,
            "snapshots_created": 0,
        }, latest_discovered_pub_time or last_run_cutoff

    print(f"\n📰 Berhasil menyaring {len(new_articles)} artikel berita baru:")
    for idx, it in enumerate(new_articles, 1):
        print(f"  [{idx}] ({it['source_domain']}) {it['title'][:65]}...")

    # 3. Initialize Gemini LLM Client
    print("\n🤖 Menginisialisasi Gemini LLM Client...")
    try:
        llm = get_llm_client(data_mode="LIVE", use_mock=False)
        print(f"✓ LLM Client siap menggunakan model: {llm.model_version}")
    except Exception as e:  # noqa: BLE001
        logger.error("Inisialisasi LLM gagal: %s", e)
        return {
            "status": "error",
            "error_message": f"Inisialisasi LLM gagal: {e}",
            "total_found": len(raw_articles),
            "new_articles_count": len(new_articles),
        }, last_run_cutoff

    pipeline = IngestExtractionPipeline(registry=registry, llm_client=llm)

    with session_factory() as session:
        print("\n⚙️  Menjalankan ekstraksi klaim berbasis bukti...")
        try:
            result = pipeline.process_batch(new_articles, session)
        except Exception as e:  # noqa: BLE001
            logger.error("Kesalahan pada tahap ekstraksi: %s", e)
            session.rollback()
            return {
                "status": "error",
                "error_message": str(e),
                "total_found": len(raw_articles),
                "new_articles_count": len(new_articles),
            }, last_run_cutoff

        print("✓ Ekstraksi Berhasil:")
        print(f"  - Artikel Baru Tersimpan     : {result.articles_saved}")
        print(f"  - Klaim Terverifikasi        : {result.claims_extracted}")
        print(f"  - Klaim Digugurkan (No Bukti): {result.claims_gated_out}")

        # 4. Event Resolution
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

        # 5. Synthesis & Snapshots
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
            f"\n🎉 SELESAI SIKLUS! {created_count} peristiwa berhasil dipublikasikan ke tab LIVE."
        )

    return {
        "status": "success",
        "total_found": len(raw_articles),
        "new_articles_count": len(new_articles),
        "skipped_duplicates": skipped_duplicate_count,
        "skipped_older": skipped_older_count,
        "claims_extracted": result.claims_extracted,
        "events_updated": len(touched_event_ids),
        "snapshots_created": created_count,
    }, latest_discovered_pub_time or last_run_cutoff


def run_live_ingest(
    source: str = "antara",
    rss_url: str | None = None,
    domain: str | None = None,
    max_articles: int = 3,
    db_url: str | None = None,
    daemon: bool = False,
    interval: int = 600,
) -> None:
    print("=" * 65)
    print(" Stay Mad — Live Data Ingestion Worker & Continuous Background Runner")
    print("=" * 65)

    if not daemon:
        summary, _ = execute_live_ingest_cycle(
            source=source,
            rss_url=rss_url,
            domain=domain,
            max_articles=max_articles,
            db_url=db_url,
        )
        print(f"Ringkasan Akhir: {summary}")
        return

    # Continuous Daemon Mode
    print("🚀 Memulai Continuous Live Ingestion Daemon...")
    print(f"   Interval polling : {interval} detik ({interval / 60:.1f} menit)")
    print(f"   Target Sumber    : {source}")
    print(f"   Maks Berita/Run  : {max_articles}")
    print("   (Tekan Ctrl+C untuk menghentikan daemon)\n")

    cycle_count = 1
    cutoff_time: datetime | None = None

    try:
        while True:
            print(
                f"\n{'=' * 25} [Siklus #{cycle_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {'=' * 25}"
            )
            summary, cutoff_time = execute_live_ingest_cycle(
                source=source,
                rss_url=rss_url,
                domain=domain,
                max_articles=max_articles,
                db_url=db_url,
                last_run_cutoff=cutoff_time,
            )
            print(
                f"✓ Siklus #{cycle_count} selesai: Ditemukan={summary.get('total_found', 0)}, "
                f"Baru={summary.get('new_articles_count', 0)}, Klaim={summary.get('claims_extracted', 0)}, "
                f"Event={summary.get('events_updated', 0)}"
            )
            cycle_count += 1
            print(f"💤 Menunggu {interval} detik sebelum polling berikutnya...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print(
            "\n\n🛑 Worker daemon dihentikan secara aman oleh pengguna. Sampai jumpa!"
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
    parser.add_argument(
        "--limit", type=int, default=3, help="Max articles to process per source"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database connection URL (Postgres or SQLite)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        default=False,
        help="Run worker in a continuous background polling loop",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="Interval between poll cycles in daemon mode (default: 600s / 10 minutes)",
    )
    args = parser.parse_args()

    run_live_ingest(
        source=args.source,
        rss_url=args.rss_url,
        domain=args.domain,
        max_articles=args.limit,
        db_url=args.db_url,
        daemon=args.daemon,
        interval=args.interval,
    )
