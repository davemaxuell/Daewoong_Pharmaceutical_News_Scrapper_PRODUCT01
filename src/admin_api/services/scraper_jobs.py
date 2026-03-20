"""Scraper job orchestration for admin controls."""

from __future__ import annotations

import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import AppLog, Job, JobSourceRun, Source
from .source_sync import ensure_sources_seeded


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRAPER_SCRIPT = PROJECT_ROOT / "src" / "multi_source_scraper.py"
FULL_PIPELINE_SCRIPT = PROJECT_ROOT / "src" / "run_pipeline.py"
HTML_MONITOR_SCRIPT = PROJECT_ROOT / "src" / "html_change_monitor.py"
SOURCE_HEALTH_SCRIPT = PROJECT_ROOT / "scripts" / "diagnose_latest_sources.py"
NEWS_DIR = PROJECT_ROOT / "data" / "news"

_PROCESS_REGISTRY: dict[str, subprocess.Popen] = {}
_REGISTRY_LOCK = threading.Lock()


def _now() -> datetime:
    return datetime.now(UTC)


def _log(db: Session, *, job_id: UUID | None, level: str, message: str, source_id: UUID | None = None) -> None:
    db.add(AppLog(job_id=job_id, source_id=source_id, level=level, message=message))
    db.commit()


def _resolve_sources(db: Session, source_codes: list[str] | None) -> list[Source]:
    ensure_sources_seeded(db)
    query = db.query(Source)
    if source_codes:
        query = query.filter(Source.code.in_(source_codes))
    else:
        query = query.filter(Source.is_enabled.is_(True))
    return query.order_by(Source.code.asc()).all()


def start_scraper_job(
    db: Session,
    *,
    requested_by: UUID,
    trigger_type: str,
    source_codes: list[str] | None,
) -> Job:
    sources = _resolve_sources(db, source_codes)
    if not sources:
        raise ValueError("No sources selected or enabled.")

    job = Job(
        job_type="scrape",
        trigger_type=trigger_type,
        status="queued",
        requested_by=requested_by,
        started_at=None,
        finished_at=None,
    )
    db.add(job)
    db.flush()

    for source in sources:
        db.add(
            JobSourceRun(
                job_id=job.id,
                source_id=source.id,
                status="queued",
                article_count=0,
                error_count=0,
            )
        )

    db.commit()
    db.refresh(job)

    thread = threading.Thread(
        target=_run_scraper_job_thread,
        args=(str(job.id), [s.code for s in sources]),
        daemon=True,
    )
    thread.start()
    return job


def _run_scraper_job_thread(job_id: str, source_codes: list[str]) -> None:
    run_output = NEWS_DIR / f"admin_run_{job_id.replace('-', '')}.json"
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SCRAPER_SCRIPT),
        "--days",
        "1",
        "--output",
        str(run_output),
        "--sources",
        *source_codes,
    ]

    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = _now()
        source_runs = db.query(JobSourceRun).filter(JobSourceRun.job_id == job.id).all()
        for sr in source_runs:
            sr.status = "running"
            sr.started_at = _now()
        db.commit()
        _log(db, job_id=job.id, level="INFO", message=f"Started scraper job with sources: {', '.join(source_codes)}")

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    with _REGISTRY_LOCK:
        _PROCESS_REGISTRY[job_id] = proc

    buffered_lines: list[str] = []
    if proc.stdout:
        for line in proc.stdout:
            text = line.strip()
            if not text:
                continue
            buffered_lines.append(text)
            if len(buffered_lines) > 50:
                buffered_lines = buffered_lines[-50:]
            with SessionLocal() as db:
                _log(db, job_id=UUID(job_id), level="INFO", message=text[:1500])

    rc = proc.wait()
    with _REGISTRY_LOCK:
        _PROCESS_REGISTRY.pop(job_id, None)

    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        source_runs = db.query(JobSourceRun).filter(JobSourceRun.job_id == job.id).all()

        if job.status == "cancelled":
            for sr in source_runs:
                if sr.status in ("queued", "running"):
                    sr.status = "skipped"
                    sr.finished_at = _now()
            db.commit()
            return

        if rc == 0:
            job.status = "success"
            for sr in source_runs:
                if sr.status in ("queued", "running"):
                    sr.status = "success"
                    sr.finished_at = _now()
            _log(db, job_id=job.id, level="INFO", message="Scraper job completed successfully.")
        else:
            job.status = "failed"
            tail = "\n".join(buffered_lines[-10:])
            job.error_message = f"Scraper exited with code {rc}"
            for sr in source_runs:
                if sr.status in ("queued", "running"):
                    sr.status = "failed"
                    sr.error_count = 1
                    sr.error_message = f"Process exit code {rc}"
                    sr.finished_at = _now()
            _log(db, job_id=job.id, level="ERROR", message=f"Scraper job failed ({rc}). {tail[:1200]}")

        job.finished_at = _now()
        db.commit()


def _run_command_job_thread(job_id: str, cmd: list[str], start_message: str, success_message: str) -> None:
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.started_at = _now()
        db.commit()
        _log(db, job_id=job.id, level="INFO", message=start_message)

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    with _REGISTRY_LOCK:
        _PROCESS_REGISTRY[job_id] = proc

    buffered_lines: list[str] = []
    if proc.stdout:
        for line in proc.stdout:
            text = line.strip()
            if not text:
                continue
            buffered_lines.append(text)
            if len(buffered_lines) > 50:
                buffered_lines = buffered_lines[-50:]
            with SessionLocal() as db:
                _log(db, job_id=UUID(job_id), level="INFO", message=text[:1500])

    rc = proc.wait()
    with _REGISTRY_LOCK:
        _PROCESS_REGISTRY.pop(job_id, None)

    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        if job.status == "cancelled":
            db.commit()
            return

        if rc == 0:
            job.status = "success"
            _log(db, job_id=job.id, level="INFO", message=success_message)
        else:
            job.status = "failed"
            tail = "\n".join(buffered_lines[-10:])
            job.error_message = f"Process exited with code {rc}"
            _log(db, job_id=job.id, level="ERROR", message=f"Job failed ({rc}). {tail[:1200]}")

        job.finished_at = _now()
        db.commit()


def start_full_pipeline_job(
    db: Session,
    *,
    requested_by: UUID,
    trigger_type: str,
) -> Job:
    job = Job(
        job_type="pipeline_full",
        trigger_type=trigger_type,
        status="queued",
        requested_by=requested_by,
        started_at=None,
        finished_at=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cmd = [sys.executable, str(FULL_PIPELINE_SCRIPT)]
    thread = threading.Thread(
        target=_run_command_job_thread,
        args=(str(job.id), cmd, "Started full pipeline run.", "Full pipeline completed successfully."),
        daemon=True,
    )
    thread.start()
    return job


def start_html_monitor_job(
    db: Session,
    *,
    requested_by: UUID,
    trigger_type: str,
) -> Job:
    job = Job(
        job_type="html_monitor",
        trigger_type=trigger_type,
        status="queued",
        requested_by=requested_by,
        started_at=None,
        finished_at=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cmd = [sys.executable, str(HTML_MONITOR_SCRIPT)]
    thread = threading.Thread(
        target=_run_command_job_thread,
        args=(str(job.id), cmd, "Started HTML monitor run.", "HTML monitor run completed successfully."),
        daemon=True,
    )
    thread.start()
    return job


def start_source_health_job(
    db: Session,
    *,
    requested_by: UUID,
    trigger_type: str,
) -> Job:
    job = Job(
        job_type="source_health",
        trigger_type=trigger_type,
        status="queued",
        requested_by=requested_by,
        started_at=None,
        finished_at=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cmd = [sys.executable, str(SOURCE_HEALTH_SCRIPT), "--days", "2"]
    thread = threading.Thread(
        target=_run_command_job_thread,
        args=(str(job.id), cmd, "Started source health diagnostics.", "Source health diagnostics completed successfully."),
        daemon=True,
    )
    thread.start()
    return job


def stop_scraper_job(db: Session, *, job_id: UUID) -> bool:
    with _REGISTRY_LOCK:
        proc = _PROCESS_REGISTRY.get(str(job_id))

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return False

    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    elif job.status not in ("queued", "running"):
        return False

    job.status = "cancelled"
    job.error_message = "Stopped by admin"
    job.finished_at = _now()

    source_runs = db.query(JobSourceRun).filter(JobSourceRun.job_id == job_id).all()
    for sr in source_runs:
        if sr.status in ("queued", "running"):
            sr.status = "skipped"
            sr.finished_at = _now()
            sr.error_message = "Stopped by admin"

    db.commit()
    _log(db, job_id=job_id, level="WARNING", message="Scraper job cancelled by admin.")
    return True


def retry_failed_sources(db: Session, *, failed_job_id: UUID, requested_by: UUID) -> Job:
    failed_source_ids = [
        source_id
        for (source_id,) in db.query(JobSourceRun.source_id)
        .filter(JobSourceRun.job_id == failed_job_id, JobSourceRun.status == "failed")
        .all()
    ]
    if not failed_source_ids:
        raise ValueError("No failed sources found for this job.")

    codes = [
        code
        for (code,) in db.query(Source.code).filter(Source.id.in_(failed_source_ids)).all()
    ]
    return start_scraper_job(
        db,
        requested_by=requested_by,
        trigger_type="retry",
        source_codes=codes,
    )
