"""Demo Pipeline Runner for Stay Mad.

Executes the vertical slice ingest, normalization, and extraction against deterministic fixtures.
Authority: DEC-0005, DEC-0006
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from backend.staymad.db.base import Base
from backend.staymad.db.session import create_db_engine, create_session_factory
from backend.staymad.ingest.pipeline import IngestExtractionPipeline
from backend.staymad.llm.factory import get_llm_client


def run_demo(fixture_path: Path, db_url: str | None = None) -> None:
    print(f"==> Launching Stay Mad Pipeline with fixture: {fixture_path}")
    if not fixture_path.exists():
        print(f"Error: Fixture file '{fixture_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"Loaded {len(articles)} raw articles from fixture.")

    # Initialize SQLite schema for demo execution
    target_url = db_url or os.getenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_db_engine(target_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    llm = get_llm_client(use_mock=True)
    pipeline = IngestExtractionPipeline(llm_client=llm)

    with session_factory() as session:
        result = pipeline.process_batch(articles, session)
        print("Pipeline Extraction Completed:")
        print(f"  - Processing Run ID: {result.processing_run_id}")
        print(f"  - Articles Saved: {result.articles_saved}")
        print(f"  - Article Versions Saved: {result.article_versions_saved}")
        print(f"  - Grounded Claims Extracted: {result.claims_extracted}")
        print(f"  - Claims Gated Out (Ungrounded): {result.claims_gated_out}")
        print(f"  - Unauthorized Sources Rejected: {result.unauthorized_rejected}")

        # Stage 04 Resolution
        from backend.staymad.resolver.manager import EventResolverManager

        resolver = EventResolverManager(
            session=session, llm_client=llm, ablation_mode="tier3"
        )
        for art_ver in result.article_versions:
            ver_claims = [
                c for c in result.claims if c.article_version_id == art_ver.id
            ]
            resolver.resolve_article_version(
                art_ver, ver_claims, result.processing_run_id
            )
        session.commit()
        print(
            f"Event Resolution Completed: {len(resolver.anchors)} canonical events formed."
        )

        # Stage 05 Intelligence & Synthesis
        from backend.staymad.db.models.event import Event
        from backend.staymad.events.manager import EventSynthesisManager

        synth_mgr = EventSynthesisManager(session=session, llm_client=llm)
        all_events = session.query(Event).all()
        for ev in all_events:
            snap = synth_mgr.synthesize_event_snapshot(
                event_id=ev.id,
                processing_run_id=result.processing_run_id,
                force_snapshot=True,
            )
            if snap:
                print(
                    f"  - Event '{snap.headline[:40]}...': "
                    f"Confidence={snap.confidence_score:.2f} ({snap.evidence_status.value}), "
                    f"Importance={snap.importance_score:.2f}, "
                    f"Timeline={len(snap.timeline_entries)} entries, "
                    f"Action={snap.actionability_level.value}"
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stay Mad Demo Pipeline")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("eval/fixtures/seed_demo_23.json"),
        help="Path to demo fixtures JSON",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL to persist data (e.g. sqlite:///backend/staymad_dev.db)",
    )
    args = parser.parse_args()
    run_demo(args.fixtures, db_url=args.db_url)
