"""Scraper control endpoints: run now, stop, retry failed sources."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..dependencies import require_admin
from ..models import User
from ..schemas import ScraperActionResponse, ScraperRunRequest
from ..services.scraper_jobs import (
    retry_failed_sources,
    start_full_pipeline_job,
    start_html_monitor_job,
    start_scraper_job,
    start_source_health_job,
    stop_scraper_job,
)


router = APIRouter(prefix="/scraper", tags=["scraper-control"])


@router.post("/run-now", response_model=ScraperActionResponse, status_code=status.HTTP_202_ACCEPTED)
def run_now(
    payload: ScraperRunRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    source_codes = payload.source_codes or None
    try:
        job = start_scraper_job(
            db,
            requested_by=admin.id,
            trigger_type="manual",
            source_codes=source_codes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="scraper.run_now",
        entity_type="job",
        entity_id=str(job.id),
        after_json={"source_codes": source_codes or "enabled-default"},
    )
    db.commit()
    return ScraperActionResponse(ok=True, message="Scraper job started.", job_id=job.id)


@router.post("/run-full-pipeline", response_model=ScraperActionResponse, status_code=status.HTTP_202_ACCEPTED)
def run_full_pipeline(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = start_full_pipeline_job(db, requested_by=admin.id, trigger_type="manual")
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="pipeline.run_full",
        entity_type="job",
        entity_id=str(job.id),
    )
    db.commit()
    return ScraperActionResponse(ok=True, message="Full pipeline job started.", job_id=job.id)


@router.post("/run-html-monitors", response_model=ScraperActionResponse, status_code=status.HTTP_202_ACCEPTED)
def run_html_monitors(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = start_html_monitor_job(db, requested_by=admin.id, trigger_type="manual")
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="monitor.run_html",
        entity_type="job",
        entity_id=str(job.id),
    )
    db.commit()
    return ScraperActionResponse(ok=True, message="HTML monitor job started.", job_id=job.id)


@router.post("/run-source-health", response_model=ScraperActionResponse, status_code=status.HTTP_202_ACCEPTED)
def run_source_health(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = start_source_health_job(db, requested_by=admin.id, trigger_type="manual")
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="monitor.run_source_health",
        entity_type="job",
        entity_id=str(job.id),
    )
    db.commit()
    return ScraperActionResponse(ok=True, message="Source health diagnostics started.", job_id=job.id)


@router.post("/run-source/{source_code}", response_model=ScraperActionResponse, status_code=status.HTTP_202_ACCEPTED)
def run_single_source(
    source_code: str = Path(..., min_length=1),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    code = source_code.strip()
    try:
        job = start_scraper_job(
            db,
            requested_by=admin.id,
            trigger_type="manual",
            source_codes=[code],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="scraper.run_source",
        entity_type="job",
        entity_id=str(job.id),
        after_json={"source_code": code},
    )
    db.commit()
    return ScraperActionResponse(ok=True, message=f"Source job started: {code}", job_id=job.id)


@router.post("/stop/{job_id}", response_model=ScraperActionResponse)
def stop_job(
    job_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stopped = stop_scraper_job(db, job_id=job_id)
    if not stopped:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Running job not found.")

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="scraper.stop",
        entity_type="job",
        entity_id=str(job_id),
    )
    db.commit()
    return ScraperActionResponse(ok=True, message="Scraper job stopped.", job_id=job_id)


@router.post("/retry-failed/{job_id}", response_model=ScraperActionResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_failed(
    job_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        new_job = retry_failed_sources(db, failed_job_id=job_id, requested_by=admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="scraper.retry_failed",
        entity_type="job",
        entity_id=str(new_job.id),
        after_json={"from_job_id": str(job_id)},
    )
    db.commit()
    return ScraperActionResponse(ok=True, message="Retry job started.", job_id=new_job.id)
