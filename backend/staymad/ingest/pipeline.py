"""Pipeline runner integrating Ingest, Normalization, Gemini Extraction, and Grounding Safety.

Authority: docs/architecture/C-gemini-architecture.md, DEC-0003, DEC-0004, DEC-0005
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.staymad.claims.verifier import filter_and_gate_claims
from backend.staymad.db.models.article import Article, ArticleVersion
from backend.staymad.db.models.claim import Claim
from backend.staymad.db.models.enums import (
    EventCategory,
    ProcessingStage,
    RunStatus,
    TimelinePrecision,
)
from backend.staymad.db.models.processing import ProcessingRun
from backend.staymad.db.models.source import Source
from backend.staymad.ingest.parser import (
    IngestedArticleVersion,
    RawArticle,
    process_raw_article,
)
from backend.staymad.ingest.sources import SourceRegistry, UnauthorizedSourceError
from backend.staymad.llm.base import BaseGeminiClient
from backend.staymad.llm.factory import get_llm_client
from backend.staymad.llm.schemas import ExtractInput
from backend.staymad.normalize.temporal import normalize_to_utc

logger = logging.getLogger(__name__)


class PipelineExecutionResult:
    """Summary of pipeline batch execution."""

    def __init__(
        self,
        processing_run_id: uuid.UUID,
        total_articles_input: int,
        articles_saved: int,
        article_versions_saved: int,
        claims_extracted: int,
        claims_gated_out: int,
        unauthorized_rejected: int,
        articles: list[Article],
        article_versions: list[ArticleVersion],
        claims: list[Claim],
    ) -> None:
        self.processing_run_id = processing_run_id
        self.total_articles_input = total_articles_input
        self.articles_saved = articles_saved
        self.article_versions_saved = article_versions_saved
        self.claims_extracted = claims_extracted
        self.claims_gated_out = claims_gated_out
        self.unauthorized_rejected = unauthorized_rejected
        self.articles = articles
        self.article_versions = article_versions
        self.claims = claims


class IngestExtractionPipeline:
    """End-to-end pipeline connecting ingest -> normalize -> Gemini extract -> grounding gate -> DB."""

    def __init__(
        self,
        registry: SourceRegistry | None = None,
        llm_client: BaseGeminiClient | None = None,
    ) -> None:
        self.registry = registry or SourceRegistry.load_from_yaml()
        self.llm_client = llm_client or get_llm_client()

    def sync_sources_to_db(self, session: Session) -> dict[str, Source]:
        """Ensure all authorized sources from config/sources.yaml exist in the database."""
        db_sources: dict[str, Source] = {}
        for src_cfg in self.registry.sources:
            stmt = select(Source).where(Source.name == src_cfg.name)
            existing = session.scalars(stmt).first()
            if not existing:
                existing = Source(
                    id=uuid.uuid4(),
                    name=src_cfg.name,
                    url=src_cfg.url,
                    source_type=src_cfg.source_type_enum,
                    source_tier=src_cfg.source_tier_enum,
                    source_family=src_cfg.source_family,
                    rate_limit_per_min=src_cfg.rate_limit_per_min,
                    retention_rule=f"Full text retention: {src_cfg.retention_days_full_text} days",
                    active=True,
                )
                session.add(existing)
                session.flush()
            db_sources[src_cfg.id] = existing
            db_sources[src_cfg.domain] = existing
        return db_sources

    def process_batch(
        self,
        raw_items: list[RawArticle | dict[str, Any]],
        session: Session,
        processing_run_id: uuid.UUID | None = None,
    ) -> PipelineExecutionResult:
        """Process a batch of raw articles into persistent Article, ArticleVersion, and Claim records."""
        source_map = self.sync_sources_to_db(session)

        run_id = processing_run_id or uuid.uuid4()
        run_record = session.get(ProcessingRun, run_id)
        if not run_record:
            run_record = ProcessingRun(
                id=run_id,
                stage=ProcessingStage.EXTRACT,
                status=RunStatus.RUNNING,
                articles_processed=0,
                model_version=self.llm_client.model_version,
                prompt_version=self.llm_client.prompt_version,
                schema_version=self.llm_client.schema_version,
            )
            session.add(run_record)
            session.flush()

        saved_articles: list[Article] = []
        saved_versions: list[ArticleVersion] = []
        saved_claims: list[Claim] = []
        unauthorized_count = 0
        gated_out_claims_count = 0

        for item in raw_items:
            try:
                ingested: IngestedArticleVersion = process_raw_article(
                    item, self.registry
                )
            except UnauthorizedSourceError as e:
                logger.warning(f"Skipping unauthorized source: {e}")
                unauthorized_count += 1
                continue

            src_db = source_map.get(ingested.source_config.id) or source_map.get(
                ingested.source_config.domain
            )
            if not src_db:
                continue

            # 1. Deduplicate or create Article
            stmt = select(Article).where(Article.content_hash == ingested.content_hash)
            article_entity = session.scalars(stmt).first()
            if not article_entity:
                article_entity = Article(
                    id=uuid.uuid4(),
                    source_id=src_db.id,
                    url=ingested.url,
                    content_hash=ingested.content_hash,
                    category=ingested.category_hint,
                    language="id",
                )
                session.add(article_entity)
                session.flush()
            saved_articles.append(article_entity)

            # 2. Immutable ArticleVersion record
            version_entity = ArticleVersion(
                id=uuid.uuid4(),
                article_id=article_entity.id,
                fetch_time=ingested.fetch_time,
                published_time=ingested.published_time,
                updated_time=ingested.updated_time,
                title=ingested.title,
                excerpt=ingested.excerpt,
                author=ingested.author,
                content_hash=ingested.content_hash,
                full_text_expires_at=ingested.full_text_expires_at,
                schema_version=ingested.schema_version,
                processing_run_id=run_id,
            )
            session.add(version_entity)
            session.flush()
            saved_versions.append(version_entity)

            # 3. Call Gemini Call 1: Extract
            extract_input = ExtractInput(
                article_version_id=str(version_entity.id),
                source_id=str(src_db.id),
                source_tier=ingested.source_config.source_tier_enum.value,
                source_family=ingested.source_config.source_family,
                title=ingested.title,
                excerpt=ingested.excerpt,
                published_time=ingested.published_time.isoformat()
                if ingested.published_time
                else None,
                updated_time=ingested.updated_time.isoformat()
                if ingested.updated_time
                else None,
                source_url=ingested.url,
            )

            extract_result = self.llm_client.extract(extract_input)

            # Update article category with LLM suggestion if confident and valid
            if extract_result.suggested_category and extract_result.suggested_category != "UNKNOWN":
                try:
                    article_entity.category = EventCategory[extract_result.suggested_category]
                except KeyError:
                    pass

            # 4. Grounding Validation & Verbatim Quote Matching Gate
            accepted_claims, rejected_info = filter_and_gate_claims(
                extract_result.claims,
                article_text=ingested.content_text or ingested.title,
                min_confidence=0.5,
            )
            gated_out_claims_count += len(rejected_info)

            # 5. Persist accepted Claim entities with normalized temporal fields
            for c in accepted_claims:
                norm_utc, norm_qual, norm_prec = normalize_to_utc(
                    raw_time=c.event_time_raw,
                    qualifier=c.event_time_qualifier,
                    source_timezone="Asia/Jakarta",
                    published_time=ingested.published_time,
                )

                prec_enum = (
                    TimelinePrecision(norm_prec)
                    if isinstance(norm_prec, TimelinePrecision)
                    else TimelinePrecision[norm_prec.upper()]
                )

                claim_entity = Claim(
                    id=uuid.uuid4(),
                    article_version_id=version_entity.id,
                    source_id=src_db.id,
                    claim_text=c.claim_text,
                    source_span=c.source_span,
                    speaker=c.speaker,
                    negation=c.negation,
                    numeric_value=c.numeric_value,
                    unit=c.unit,
                    location_raw=c.location_raw,
                    event_time_raw=c.event_time_raw,
                    event_time=norm_utc,
                    event_time_precision=prec_enum,
                    event_time_qualifier=norm_qual,
                    source_timezone="Asia/Jakarta",
                    extraction_confidence=c.extraction_confidence,
                    language="id",
                    model_version=self.llm_client.model_version,
                    prompt_version=self.llm_client.prompt_version,
                    schema_version=self.llm_client.schema_version,
                    processing_run_id=run_id,
                )
                session.add(claim_entity)
                saved_claims.append(claim_entity)

        # Update processing run stats
        run_record.articles_processed = len(saved_articles)
        run_record.status = RunStatus.COMPLETED
        session.commit()

        return PipelineExecutionResult(
            processing_run_id=run_id,
            total_articles_input=len(raw_items),
            articles_saved=len(saved_articles),
            article_versions_saved=len(saved_versions),
            claims_extracted=len(saved_claims),
            claims_gated_out=gated_out_claims_count,
            unauthorized_rejected=unauthorized_count,
            articles=saved_articles,
            article_versions=saved_versions,
            claims=saved_claims,
        )
