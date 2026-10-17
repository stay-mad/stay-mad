"""Events router implementing 7 event-intelligence endpoints.

Authority: docs/contracts/openapi.yaml, docs/decisions.md (DEC-0001, DEC-0006, Conflict #7)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.staymad.api.dependencies import get_db
from backend.staymad.api.schemas import (
    ActionabilityLevel,
    ActionItem,
    AnalysisResponse,
    ChangeCategory,
    ChangeItem,
    ChangesResponse,
    ChangeType,
    ConfidenceBucket,
    ConfidenceComponents,
    ConfidenceSignals,
    ConflictItem,
    DataMode,
    EventCategory,
    EventDetailResponse,
    EventListResponse,
    EventSummary,
    EventSummaryStats,
    EvidenceField,
    EvidenceStatus,
    GeoLevel,
    Location,
    ProcessingResponse,
    SourceItem,
    SourcesResponse,
    SourceTier,
    TimelinePrecision,
    TimelineQualifier,
    TimelineResponse,
    VerificationLevel,
)
from backend.staymad.api.schemas import (
    TimelineEntry as TimelineEntrySchema,
)
from backend.staymad.confidence.calculator import calculate_confidence
from backend.staymad.db.models.audit import EventMembershipAudit
from backend.staymad.db.models.enums import (
    DataMode as DbDataMode,
)
from backend.staymad.db.models.enums import (
    EventCategory as DbEventCategory,
)
from backend.staymad.db.models.event import Event, EventChange, EventSnapshot
from backend.staymad.db.models.location import Location as LocationModel
from backend.staymad.db.models.timeline import TimelineEntry
from backend.staymad.timeline.builder import format_timeline_display_time

router = APIRouter(prefix="/events", tags=["events"])


def _derive_signals_text(
    claims: list, conflicts: list, snapshot: EventSnapshot
) -> list[str]:
    """Derive human-readable UI explanations based on grounded data (DEC-0006)."""
    signals = []
    has_gov = any(
        c.source
        and c.source.source_family
        and c.source.source_family.startswith("GOV_")
        for c in claims
    )
    if has_gov:
        signals.append("✓ Dikonfirmasi oleh otoritas resmi pemerintah")

    families = {
        c.source.source_family
        for c in claims
        if c.source and c.source.source_family and c.source.source_family != "UNKNOWN"
    }
    if len(families) >= 2:
        signals.append(
            f"✓ Didukung oleh {len(families)} keluarga sumber berita independen"
        )
    elif len(families) == 1:
        signals.append("• Informasi berasal dari sumber tunggal terverifikasi")

    unresolved = [cf for cf in conflicts if not cf.resolved]
    if unresolved:
        signals.append(
            f"⚠ Terdapat {len(unresolved)} pertentangan data yang sedang ditangani"
        )
    elif conflicts:
        signals.append(
            "✓ Perbedaan laporan terdahulu telah diselesaikan pembaruan resmi"
        )

    if snapshot.actionability_level == ActionabilityLevel.ACTION_REQUIRED:
        signals.append(
            "⚡ Tindakan keselamatan resmi diinstruksikan oleh pihak berwenang"
        )

    return signals


def build_confidence_signals(
    event: Event,
    snapshot: EventSnapshot,
    claims: list,
    conflicts: list,
) -> ConfidenceSignals:
    """Build grounded ConfidenceSignals with 5 component breakdown and text signals."""
    conf_res = calculate_confidence(claims, conflicts=conflicts)

    c_bucket = (
        ConfidenceBucket(snapshot.confidence_bucket.value)
        if hasattr(snapshot.confidence_bucket, "value")
        else ConfidenceBucket(str(snapshot.confidence_bucket))
    )
    e_status = (
        EvidenceStatus(snapshot.evidence_status.value)
        if hasattr(snapshot.evidence_status, "value")
        else EvidenceStatus(str(snapshot.evidence_status))
    )
    v_level = (
        VerificationLevel(snapshot.verification_level.value)
        if hasattr(snapshot.verification_level, "value")
        else VerificationLevel(str(snapshot.verification_level))
    )

    signals_text = _derive_signals_text(claims, conflicts, snapshot)

    return ConfidenceSignals(
        confidence_score=snapshot.confidence_score,
        confidence_bucket=c_bucket,
        evidence_status=e_status,
        verification_level=v_level,
        components=ConfidenceComponents(**conf_res.components),
        signals_text=signals_text,
    )


def _to_geo_level(raw: Any) -> GeoLevel:
    val = (raw.value if hasattr(raw, "value") else str(raw)).lower()
    return GeoLevel(val)


def _to_event_category(raw: Any) -> EventCategory:
    val = (raw.value if hasattr(raw, "value") else str(raw)).lower()
    return EventCategory(val)


def _to_data_mode(raw: Any) -> DataMode:
    val = (raw.value if hasattr(raw, "value") else str(raw)).lower()
    return DataMode(val)


def build_event_summary(
    event: Event,
    snapshot: EventSnapshot,
    session: Session,
) -> EventSummary:
    """Transform canonical Event and latest EventSnapshot to EventSummary."""
    claims = [ec.claim for ec in event.event_claims if ec.claim is not None]
    conflicts = list(event.conflicts)
    conf_signals = build_confidence_signals(event, snapshot, claims, conflicts)

    loc = None
    if event.primary_location:
        pl = event.primary_location
        loc = Location(
            id=pl.id,
            city=pl.city,
            district=pl.district,
            province=pl.province,
            country=pl.country or "Indonesia",
            geo_level=_to_geo_level(pl.geo_level),
            canonical_name=pl.canonical_name,
        )

    cat = _to_event_category(event.category)
    act_level = (
        ActionabilityLevel(snapshot.actionability_level.value)
        if hasattr(snapshot.actionability_level, "value")
        else ActionabilityLevel(str(snapshot.actionability_level))
    )
    data_mode = _to_data_mode(snapshot.data_mode)

    return EventSummary(
        id=event.id,
        category=cat,
        headline=snapshot.headline,
        primary_location=loc,
        time_window_start=event.time_window_start,
        time_window_end=event.time_window_end,
        confidence_signals=conf_signals,
        importance_score=snapshot.importance_score,
        urgency_score=snapshot.urgency_score,
        actionability_level=act_level,
        snapshot_id=snapshot.id,
        data_mode=data_mode,
        last_processed_at=snapshot.last_processed_at,
        processing_run_id=snapshot.processing_run_id,
    )


@router.get("", response_model=EventListResponse)
def list_events(
    category: EventCategory | None = None,
    location: str | None = None,
    location_province: str | None = None,
    location_city: str | None = None,
    data_mode: DataMode | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    offset: Annotated[int, Query(ge=0)] = 0,
    since: datetime | None = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """List published events returning the latest EventSnapshot per canonical event."""
    subq = (
        select(
            EventSnapshot.event_id,
            func.max(EventSnapshot.version_number).label("max_ver"),
        )
        .group_by(EventSnapshot.event_id)
        .subquery()
    )

    stmt = (
        select(EventSnapshot, Event)
        .join(
            subq,
            (EventSnapshot.event_id == subq.c.event_id)
            & (EventSnapshot.version_number == subq.c.max_ver),
        )
        .join(Event, Event.id == EventSnapshot.event_id)
    )

    if category is not None:
        try:
            db_cat = DbEventCategory[category.value.upper()]
            stmt = stmt.where(Event.category == db_cat)
        except (KeyError, ValueError):
            stmt = stmt.where(
                Event.category.in_([category.value, category.value.upper()])
            )

    if data_mode is not None:
        try:
            db_mode = DbDataMode[data_mode.value.upper()]
            stmt = stmt.where(EventSnapshot.data_mode == db_mode)
        except (KeyError, ValueError):
            stmt = stmt.where(
                EventSnapshot.data_mode.in_([data_mode.value, data_mode.value.upper()])
            )

    if since is not None:
        stmt = stmt.where(EventSnapshot.last_processed_at > since)

    # Headline keyword search (Item A2.4)
    if q is not None and q.strip():
        q_clean = q.strip()
        stmt = stmt.where(EventSnapshot.headline.ilike(f"%{q_clean}%"))

    # Location filtering (Item A1 & Decision A1.4: Strict Local Only)
    if (
        location is not None
        or location_province is not None
        or location_city is not None
    ):
        stmt = stmt.join(LocationModel, Event.primary_location_id == LocationModel.id)

        loc_conditions = []
        if location is not None and location.strip():
            loc_term = f"%{location.strip()}%"
            loc_conditions.append(
                LocationModel.province.ilike(loc_term)
                | LocationModel.city.ilike(loc_term)
                | LocationModel.canonical_name.ilike(loc_term)
            )
        if location_province is not None and location_province.strip():
            prov_term = f"%{location_province.strip()}%"
            # Support province matching and fallback city/canonical matching for legacy calls
            loc_conditions.append(
                LocationModel.province.ilike(prov_term)
                | LocationModel.city.ilike(prov_term)
                | LocationModel.canonical_name.ilike(prov_term)
            )
        if location_city is not None and location_city.strip():
            city_term = f"%{location_city.strip()}%"
            loc_conditions.append(
                LocationModel.city.ilike(city_term)
                | LocationModel.canonical_name.ilike(city_term)
            )
        for cond in loc_conditions:
            stmt = stmt.where(cond)

    stmt = stmt.order_by(desc(EventSnapshot.importance_score))

    all_matched = db.execute(stmt).all()
    total = len(all_matched)

    # Compute aggregate summary stats over all filtered items (Item A2.5)
    need_to_know = sum(
        1
        for snap, ev in all_matched
        if (getattr(snap, "urgency_score", 0.0) or 0.0) >= 0.75
        or (getattr(snap, "importance_score", 0.0) or 0.0) >= 0.85
    )
    official_primary = sum(
        1
        for snap, ev in all_matched
        if getattr(snap.verification_level, "value", str(snap.verification_level))
        == "OFFICIAL_PRIMARY"
    )
    conflicts = sum(
        1
        for snap, ev in all_matched
        if getattr(snap.evidence_status, "value", str(snap.evidence_status))
        == "CONFLICTING"
    )
    stats = EventSummaryStats(
        total=total,
        need_to_know=need_to_know,
        official_primary=official_primary,
        conflicts=conflicts,
    )

    paged_results = all_matched[offset : offset + limit]
    summaries = [build_event_summary(ev, snap, db) for snap, ev in paged_results]

    resolved_mode = data_mode or (
        summaries[0].data_mode if summaries else DataMode.LIVE
    )
    return EventListResponse(
        events=summaries,
        total=total,
        limit=limit,
        offset=offset,
        data_mode=resolved_mode,
        summary_stats=stats,
    )


@router.get("/{id}", response_model=EventDetailResponse)
def get_event(
    id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve full detail for an event snapshot."""
    event = db.get(Event, id)
    if not event or not event.snapshots:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Event dengan ID '{id}' tidak ditemukan",
            },
        )

    snapshot = event.snapshots[-1]
    claims = [ec.claim for ec in event.event_claims if ec.claim is not None]
    conflicts = list(event.conflicts)
    conf_signals = build_confidence_signals(event, snapshot, claims, conflicts)

    def _parse_claim_ids(cids: Any) -> list[uuid.UUID]:
        if not cids:
            return []
        parsed = []
        for x in cids:
            if isinstance(x, uuid.UUID):
                parsed.append(x)
            else:
                try:
                    parsed.append(uuid.UUID(str(x)))
                except ValueError:
                    parsed.append(uuid.uuid5(uuid.NAMESPACE_DNS, str(x)))
        return parsed

    conflict_summary = None
    if snapshot.conflict_summary:
        conflict_summary = EvidenceField(
            text=snapshot.conflict_summary,
            evidence_claim_ids=_parse_claim_ids(
                snapshot.conflict_summary_evidence_claim_ids
            ),
        )
    elif conflicts:
        cf_texts = []
        cf_claim_ids = []
        for cf in conflicts:
            res_str = "selesai" if cf.resolved else "belum terselesaikan"
            cf_texts.append(
                f"Pertentangan data {cf.field_name}: '{cf.value_a}' vs '{cf.value_b}' ({res_str})"
            )
            cf_claim_ids.extend([cf.claim_a_id, cf.claim_b_id])
        conflict_summary = EvidenceField(
            text="; ".join(cf_texts),
            evidence_claim_ids=_parse_claim_ids(list(dict.fromkeys(cf_claim_ids))),
        )

    action_items = []
    for act in event.actions:
        if act.snapshot_id == snapshot.id or act.snapshot_id is None:
            a_lvl = (
                ActionabilityLevel(act.action_level.value)
                if hasattr(act.action_level, "value")
                else ActionabilityLevel(str(act.action_level))
            )
            action_items.append(
                ActionItem(
                    action_level=a_lvl,
                    action_text=act.action_text,
                    evidence_claim_ids=[
                        uuid.UUID(str(cid)) for cid in act.evidence_claim_ids
                    ],
                )
            )

    loc = None
    if event.primary_location:
        pl = event.primary_location
        loc = Location(
            id=pl.id,
            city=pl.city,
            district=pl.district,
            province=pl.province,
            country=pl.country or "Indonesia",
            geo_level=_to_geo_level(pl.geo_level),
            canonical_name=pl.canonical_name,
        )

    cat = _to_event_category(event.category)
    act_level = (
        ActionabilityLevel(snapshot.actionability_level.value)
        if hasattr(snapshot.actionability_level, "value")
        else ActionabilityLevel(str(snapshot.actionability_level))
    )
    data_mode = _to_data_mode(snapshot.data_mode)

    return EventDetailResponse(
        id=event.id,
        snapshot_id=snapshot.id,
        category=cat,
        headline=snapshot.headline,
        primary_location=loc,
        time_window_start=event.time_window_start,
        what_happened=EvidenceField(
            text=snapshot.what_happened,
            evidence_claim_ids=_parse_claim_ids(
                snapshot.what_happened_evidence_claim_ids
            ),
        ),
        why_it_matters=EvidenceField(
            text=snapshot.why_it_matters,
            evidence_claim_ids=_parse_claim_ids(
                snapshot.why_it_matters_evidence_claim_ids
            ),
        )
        if snapshot.why_it_matters
        else None,
        who_is_affected=EvidenceField(
            text=snapshot.who_is_affected,
            evidence_claim_ids=_parse_claim_ids(
                snapshot.who_is_affected_evidence_claim_ids
            ),
        )
        if snapshot.who_is_affected
        else None,
        what_is_unknown=EvidenceField(
            text=snapshot.what_is_unknown,
            evidence_claim_ids=[],
        )
        if snapshot.what_is_unknown
        else None,
        conflict_summary=conflict_summary,
        actions=action_items,
        confidence_signals=conf_signals,
        importance_score=snapshot.importance_score,
        urgency_score=snapshot.urgency_score,
        actionability_level=act_level,
        data_mode=data_mode,
        last_processed_at=snapshot.last_processed_at,
        processing_run_id=snapshot.processing_run_id,
    )


@router.get("/{id}/timeline", response_model=TimelineResponse)
def get_event_timeline(
    id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    snapshot_id: uuid.UUID | None = None,
):
    """Chronological timeline for an event snapshot in Asia/Jakarta (WIB)."""
    event = db.get(Event, id)
    if not event or not event.snapshots:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Event dengan ID '{id}' tidak ditemukan",
            },
        )

    if snapshot_id is not None:
        snapshot = db.get(EventSnapshot, snapshot_id)
        if not snapshot or snapshot.event_id != event.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"Snapshot dengan ID '{snapshot_id}' tidak ditemukan",
                },
            )
    else:
        snapshot = event.snapshots[-1]

    entries_db = db.scalars(
        select(TimelineEntry)
        .where(TimelineEntry.snapshot_id == snapshot.id)
        .order_by(TimelineEntry.order_index.asc(), TimelineEntry.event_time.asc())
    ).all()

    entries = []
    for te in entries_db:
        display_t = format_timeline_display_time(
            event_time=te.event_time,
            precision=te.event_time_precision,
            qualifier=te.event_time_qualifier,
        )
        prec = (
            TimelinePrecision(te.event_time_precision.value)
            if hasattr(te.event_time_precision, "value")
            else TimelinePrecision(str(te.event_time_precision))
        )
        qual = (
            TimelineQualifier(te.event_time_qualifier)
            if te.event_time_qualifier in [q.value for q in TimelineQualifier]
            else te.event_time_qualifier
        )
        entries.append(
            TimelineEntrySchema(
                id=te.id,
                event_time=te.event_time,
                display_time=display_t,
                event_time_precision=prec,
                event_time_qualifier=qual,
                description=te.description,
                evidence_claim_ids=[
                    uuid.UUID(str(cid)) for cid in te.evidence_claim_ids
                ],
                order_index=te.order_index,
            )
        )

    return TimelineResponse(
        event_id=event.id,
        snapshot_id=snapshot.id,
        entries=entries,
        processing_run_id=snapshot.processing_run_id,
    )


@router.get("/{id}/sources", response_model=SourcesResponse)
def get_event_sources(
    id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """List original sources with source_family conglomeration groupings."""
    event = db.get(Event, id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Event dengan ID '{id}' tidak ditemukan",
            },
        )

    snapshot = event.snapshots[-1] if event.snapshots else None
    claims = [ec.claim for ec in event.event_claims if ec.claim is not None]

    seen_versions = set()
    source_items = []
    source_families = set()

    for c in claims:
        art_ver = c.article_version
        if not art_ver or art_ver.id in seen_versions:
            continue
        seen_versions.add(art_ver.id)

        art = art_ver.article
        src = art.source if art else c.source
        src_id = src.id if src else uuid.uuid4()
        src_name = src.name if src else "Sumber Tidak Diketahui"
        src_tier_raw = src.source_tier if src else SourceTier.TIER_2
        src_tier = (
            SourceTier(src_tier_raw.value)
            if hasattr(src_tier_raw, "value")
            else SourceTier(str(src_tier_raw))
        )
        src_fam = src.source_family if src else "UNKNOWN"
        if src_fam:
            source_families.add(src_fam)

        art_url = art.url if art else "https://news.example.com"
        pub_time = art_ver.published_time or art_ver.fetch_time

        source_items.append(
            SourceItem(
                source_id=src_id,
                name=src_name,
                source_tier=src_tier,
                source_family=src_fam,
                article_url=art_url,
                published_time=pub_time,
                article_version_id=art_ver.id,
            )
        )

    proc_id = (
        snapshot.processing_run_id
        if snapshot
        else (claims[0].processing_run_id if claims else uuid.uuid4())
    )

    return SourcesResponse(
        event_id=event.id,
        sources=source_items,
        unique_source_families=len(source_families),
        processing_run_id=proc_id,
    )


@router.get("/{id}/changes", response_model=ChangesResponse)
def get_event_changes(
    id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    from_snapshot_id: uuid.UUID | None = None,
    to_snapshot_id: uuid.UUID | None = None,
):
    """Retrieve structured material delta changes between snapshots."""
    event = db.get(Event, id)
    if not event or not event.snapshots:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Event dengan ID '{id}' tidak ditemukan",
            },
        )

    if to_snapshot_id is not None:
        to_snap = db.get(EventSnapshot, to_snapshot_id)
        if not to_snap or to_snap.event_id != event.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"to_snapshot_id '{to_snapshot_id}' tidak ditemukan untuk event ini",
                },
            )
    else:
        to_snap = event.snapshots[-1]

    if from_snapshot_id is not None:
        from_snap = db.get(EventSnapshot, from_snapshot_id)
        if not from_snap or from_snap.event_id != event.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"from_snapshot_id '{from_snapshot_id}' tidak ditemukan untuk event ini",
                },
            )
    else:
        from_snap = event.snapshots[-2] if len(event.snapshots) >= 2 else None

    stmt = select(EventChange).where(
        EventChange.event_id == event.id,
        EventChange.to_snapshot_id == to_snap.id,
    )
    if from_snap is not None:
        stmt = stmt.where(EventChange.from_snapshot_id == from_snap.id)

    changes_db = db.scalars(stmt).all()
    items = []
    for chg in changes_db:
        cat = None
        if chg.change_category:
            cat = (
                ChangeCategory(chg.change_category.value)
                if hasattr(chg.change_category, "value")
                else ChangeCategory(str(chg.change_category))
            )
        c_type = (
            ChangeType(chg.change_type.value)
            if hasattr(chg.change_type, "value")
            else ChangeType(str(chg.change_type))
        )
        items.append(
            ChangeItem(
                id=chg.id,
                change_type=c_type,
                change_category=cat,
                field_name=chg.field_name,
                before_value=chg.before_value,
                after_value=chg.after_value,
                evidence_claim_ids=[
                    uuid.UUID(str(cid)) for cid in chg.evidence_claim_ids
                ],
            )
        )

    return ChangesResponse(
        event_id=event.id,
        from_snapshot_id=from_snap.id if from_snap else None,
        to_snapshot_id=to_snap.id,
        changes=items,
        material_change_count=len(items),
    )


@router.get("/{id}/analysis", response_model=AnalysisResponse)
def get_event_analysis(
    id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve event analysis, factual conflicts, and claim metrics."""
    event = db.get(Event, id)
    if not event or not event.snapshots:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Event dengan ID '{id}' tidak ditemukan",
            },
        )

    snapshot = event.snapshots[-1]
    claims = [ec.claim for ec in event.event_claims if ec.claim is not None]
    conflicts = list(event.conflicts)
    conf_signals = build_confidence_signals(event, snapshot, claims, conflicts)

    conflict_items = []
    conflicting_claims = set()
    for cf in conflicts:
        conflict_items.append(
            ConflictItem(
                id=cf.id,
                field_name=cf.field_name,
                claim_a_id=cf.claim_a_id,
                claim_b_id=cf.claim_b_id,
                value_a=cf.value_a,
                value_b=cf.value_b,
                context=cf.context,
                resolved=cf.resolved,
            )
        )
        if not cf.resolved:
            conflicting_claims.add(cf.claim_a_id)
            conflicting_claims.add(cf.claim_b_id)

    return AnalysisResponse(
        event_id=event.id,
        snapshot_id=snapshot.id,
        conflicts=conflict_items,
        confidence_signals=conf_signals,
        claim_count=len(claims),
        conflicting_claim_count=len(conflicting_claims),
        processing_run_id=snapshot.processing_run_id,
    )


@router.get("/{id}/processing", response_model=ProcessingResponse)
def get_event_processing(
    id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    snapshot_id: uuid.UUID | None = None,
):
    """Screen 3 Processing & Evidence transparency data (Conflict #7, no CoT)."""
    event = db.get(Event, id)
    if not event or not event.snapshots:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Event dengan ID '{id}' tidak ditemukan",
            },
        )

    if snapshot_id is not None:
        snapshot = db.get(EventSnapshot, snapshot_id)
        if not snapshot or snapshot.event_id != event.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"Snapshot dengan ID '{snapshot_id}' tidak ditemukan",
                },
            )
    else:
        snapshot = event.snapshots[-1]

    claims = [ec.claim for ec in event.event_claims if ec.claim is not None]
    conflicts = list(event.conflicts)
    conf_signals = build_confidence_signals(event, snapshot, claims, conflicts)

    art_ver_ids = {c.article_version_id for c in claims if c.article_version_id}
    articles_analyzed = len(art_ver_ids)
    claims_extracted = len(claims)

    audits = (
        db.scalars(
            select(EventMembershipAudit).where(
                EventMembershipAudit.article_version_id.in_(art_ver_ids)
            )
        ).all()
        if art_ver_ids
        else []
    )

    candidate_ids = set()
    reason_codes = []
    for aud in audits:
        if aud.candidate_event_ids:
            candidate_ids.update(aud.candidate_event_ids)
        if aud.decision_reason_codes:
            for rc in aud.decision_reason_codes:
                if rc not in reason_codes:
                    reason_codes.append(rc)

    if not reason_codes:
        reason_codes = ["LOC_MATCH", "CORROBORATED"]

    candidate_events_count = len(candidate_ids) if candidate_ids else 0

    timeline_count = len(
        db.scalars(
            select(TimelineEntry.id).where(TimelineEntry.snapshot_id == snapshot.id)
        ).all()
    )

    data_mode = _to_data_mode(snapshot.data_mode)

    return ProcessingResponse(
        event_id=event.id,
        snapshot_id=snapshot.id,
        processing_run_id=snapshot.processing_run_id,
        correlation_id=str(snapshot.processing_run_id),
        articles_analyzed=articles_analyzed,
        claims_extracted=claims_extracted,
        candidate_events_considered=candidate_events_count,
        timeline_entries=timeline_count,
        conflicts_detected=len(conflicts),
        decision_reason_codes=reason_codes,
        resolution_tier_used="TIER_2",
        confidence_signals=conf_signals,
        model_version=snapshot.model_version,
        prompt_version=snapshot.prompt_version,
        schema_version=snapshot.schema_version,
        last_processed_at=snapshot.last_processed_at,
        data_mode=data_mode,
    )
