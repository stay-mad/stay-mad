"""Background jobs endpoints for asynchronous ingestion and processing.

Authority: docs/decisions.md (DEC-0006), docs/architecture/J-cloud-run-architecture.md
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from backend.staymad.api.schemas import (
    IngestJobRequest,
    JobDetailResponse,
    JobIngestResponse,
)
from backend.staymad.jobs.live_ingest import execute_live_ingest_cycle

logger = logging.getLogger("staymad.api.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])

# In-memory job state tracker
_JOB_HISTORY: dict[str, dict[str, Any]] = {}


def _run_ingest_background(
    job_id: str,
    source: str,
    limit: int,
    db_url: str | None,
) -> None:
    """Asynchronous background worker execution for live news ingestion."""
    logger.info(
        "Starting background ingestion task job_id=%s source=%s limit=%d",
        job_id,
        source,
        limit,
    )
    if job_id in _JOB_HISTORY:
        _JOB_HISTORY[job_id]["status"] = "running"
        _JOB_HISTORY[job_id]["started_at"] = datetime.now(UTC)

    try:
        summary, _ = execute_live_ingest_cycle(
            source=source,
            max_articles=limit,
            db_url=db_url,
        )
        if job_id in _JOB_HISTORY:
            _JOB_HISTORY[job_id]["status"] = "completed"
            _JOB_HISTORY[job_id]["completed_at"] = datetime.now(UTC)
            _JOB_HISTORY[job_id]["summary"] = summary
        logger.info(
            "Background ingestion task job_id=%s completed successfully: %s",
            job_id,
            summary,
        )
    except Exception as exc:
        logger.exception("Background ingestion task job_id=%s failed", job_id)
        if job_id in _JOB_HISTORY:
            _JOB_HISTORY[job_id]["status"] = "failed"
            _JOB_HISTORY[job_id]["completed_at"] = datetime.now(UTC)
            _JOB_HISTORY[job_id]["error"] = str(exc)


@router.post(
    "/ingest",
    response_model=JobIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous news ingestion job",
)
def trigger_live_ingestion(
    background_tasks: BackgroundTasks,
    request: IngestJobRequest | None = None,
    source: str | None = Query(None, description="Source key or 'all'"),
    limit: int | None = Query(None, description="Max articles to process per source"),
):
    """Trigger an asynchronous live news ingestion cycle per DEC-0006.

    Returns HTTP 202 Accepted immediately with a unique job_id. The ingestion pipeline
    runs entirely in background tasks without blocking the API or freezing the client UI.
    """
    effective_source = (request.source if request else None) or source or "all"
    effective_limit = (request.limit if request else None) or limit or 3
    effective_db = request.db_url if request else None

    job_id = f"job_ingest_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(UTC)

    _JOB_HISTORY[job_id] = {
        "job_id": job_id,
        "status": "accepted",
        "source": effective_source,
        "limit": effective_limit,
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "summary": None,
        "error": None,
    }

    # Queue execution to background worker
    background_tasks.add_task(
        _run_ingest_background,
        job_id=job_id,
        source=effective_source,
        limit=effective_limit,
        db_url=effective_db,
    )

    return JobIngestResponse(
        status="accepted",
        job_id=job_id,
        message="Live data ingestion job queued successfully in background.",
        source=effective_source,
        limit=effective_limit,
        created_at=created_at,
    )


@router.get(
    "/ingest/{job_id}",
    response_model=JobDetailResponse,
    summary="Get status and summary of an ingestion job",
)
def get_job_status(job_id: str):
    """Inspect progress and outcome of an asynchronous ingestion job."""
    if job_id not in _JOB_HISTORY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return JobDetailResponse(**_JOB_HISTORY[job_id])


@router.get(
    "/ingest",
    response_model=list[JobDetailResponse],
    summary="List recent ingestion jobs",
)
def list_recent_jobs(limit: int = Query(10, ge=1, le=50)):
    """List recent background ingestion jobs."""
    jobs = list(_JOB_HISTORY.values())[-limit:]
    jobs.reverse()
    return [JobDetailResponse(**j) for j in jobs]
