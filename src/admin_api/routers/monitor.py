"""Run monitor and log viewer routes."""

from __future__ import annotations

import json
import csv
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import case, func
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import AppLog, EmailCampaign, EmailDelivery, Job, JobSourceRun, Recipient, RecipientTeamMap, Source, Team, User
from ..schemas import AppLogResponse, JobResponse, JobSourceRunResponse


router = APIRouter(tags=["monitor"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_NEWS_DIR = PROJECT_ROOT / "data" / "news"
DATA_MONITORS_DIR = PROJECT_ROOT / "data" / "monitors"
DATA_DIAGNOSTICS_DIR = PROJECT_ROOT / "data" / "diagnostics"


def _load_source_health_payload() -> dict | None:
    latest_file = DATA_DIAGNOSTICS_DIR / "latest_source_health.json"
    if not latest_file.exists():
        candidates = sorted(
            DATA_DIAGNOSTICS_DIR.glob("latest_sources_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            latest_file = candidates[0]

    if not latest_file.exists():
        return None

    with latest_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    results = payload.get("results", [])
    payload["file"] = str(latest_file)
    payload["counts"] = {
        "healthy": sum(1 for item in results if item.get("status") == "healthy"),
        "stale": sum(1 for item in results if item.get("status") == "stale"),
        "blocked": sum(1 for item in results if item.get("status") == "blocked"),
        "unknown": sum(1 for item in results if item.get("status") == "unknown"),
        "error": sum(1 for item in results if item.get("status") == "error"),
    }
    return payload


def _team_delivery_summary(db: Session, since: datetime) -> list[dict]:
    rows = (
        db.query(
            Team.name,
            func.count(EmailDelivery.id),
            func.sum(case((EmailDelivery.status == "failed", 1), else_=0)),
            func.max(EmailDelivery.sent_at),
        )
        .join(RecipientTeamMap, RecipientTeamMap.team_id == Team.id)
        .join(Recipient, Recipient.id == RecipientTeamMap.recipient_id)
        .join(EmailDelivery, EmailDelivery.recipient_id == Recipient.id)
        .join(EmailCampaign, EmailCampaign.id == EmailDelivery.campaign_id)
        .filter(EmailCampaign.created_at >= since)
        .group_by(Team.name)
        .order_by(Team.name.asc())
        .all()
    )
    return [
        {
            "team_name": team_name,
            "deliveries_total": int(total or 0),
            "deliveries_failed": int(failed or 0),
            "deliveries_sent": max(0, int(total or 0) - int(failed or 0)),
            "latest_sent_at": latest_sent_at,
        }
        for team_name, total, failed, latest_sent_at in rows
    ]


def _campaign_team_map(db: Session, campaign_ids: list[UUID]) -> dict[UUID, list[str]]:
    if not campaign_ids:
        return {}
    rows = (
        db.query(EmailDelivery.campaign_id, Team.name)
        .join(Recipient, Recipient.id == EmailDelivery.recipient_id)
        .join(RecipientTeamMap, RecipientTeamMap.recipient_id == Recipient.id)
        .join(Team, Team.id == RecipientTeamMap.team_id)
        .filter(EmailDelivery.campaign_id.in_(campaign_ids))
        .distinct()
        .all()
    )
    mapping: dict[UUID, set[str]] = {}
    for campaign_id, team_name in rows:
        mapping.setdefault(campaign_id, set()).add(team_name)
    return {campaign_id: sorted(team_names) for campaign_id, team_names in mapping.items()}


def build_admin_report_payload(days: int, db: Session) -> dict:
    now = datetime.now().astimezone()
    since = now - timedelta(days=days)

    jobs = db.query(Job).filter(Job.created_at >= since).all()
    logs = db.query(AppLog).filter(AppLog.created_at >= since).all()
    campaigns = db.query(EmailCampaign).filter(EmailCampaign.created_at >= since).order_by(EmailCampaign.created_at.desc()).all()
    campaign_ids = [campaign.id for campaign in campaigns]

    deliveries_total = 0
    deliveries_failed = 0
    latest_email_sent_at = None
    if campaign_ids:
        deliveries_total = (
            db.query(func.count(EmailDelivery.id))
            .filter(EmailDelivery.campaign_id.in_(campaign_ids))
            .scalar()
            or 0
        )
        deliveries_failed = (
            db.query(func.count(EmailDelivery.id))
            .filter(EmailDelivery.campaign_id.in_(campaign_ids), EmailDelivery.status == "failed")
            .scalar()
            or 0
        )
        latest_email_sent_at = max((campaign.sent_at for campaign in campaigns if campaign.sent_at), default=None)

    source_health = _load_source_health_payload()
    team_summary = _team_delivery_summary(db, since)
    campaign_team_names = _campaign_team_map(db, campaign_ids)
    recent_campaigns = [
        {
            "id": str(campaign.id),
            "subject": campaign.subject,
            "team_names": campaign_team_names.get(campaign.id, []),
            "status": campaign.status,
            "article_count": campaign.article_count,
            "created_at": campaign.created_at,
            "sent_at": campaign.sent_at,
        }
        for campaign in campaigns[:10]
    ]

    return {
        "generated_at": now.isoformat(),
        "days": days,
        "runs": {
            "total": len(jobs),
            "success": sum(1 for job in jobs if job.status == "success"),
            "failed": sum(1 for job in jobs if job.status == "failed"),
            "running": sum(1 for job in jobs if job.status == "running"),
            "queued": sum(1 for job in jobs if job.status == "queued"),
            "last_successful_pipeline_at": max(
                (job.finished_at for job in jobs if job.job_type == "pipeline_full" and job.status == "success"),
                default=None,
            ),
            "last_successful_monitor_at": max(
                (job.finished_at for job in jobs if job.job_type == "html_monitor" and job.status == "success"),
                default=None,
            ),
        },
        "logs": {
            "errors": sum(1 for log in logs if log.level == "ERROR"),
            "warnings": sum(1 for log in logs if log.level == "WARNING"),
        },
        "emails": {
            "campaigns_total": len(campaigns),
            "campaigns_sent": sum(1 for campaign in campaigns if campaign.status == "sent"),
            "campaigns_failed": sum(1 for campaign in campaigns if campaign.status == "failed"),
            "deliveries_total": deliveries_total,
            "deliveries_failed": deliveries_failed,
            "latest_sent_at": latest_email_sent_at,
            "team_summary": team_summary,
            "recent_campaigns": recent_campaigns,
        },
        "source_health": (
            {
                "generated_at": source_health.get("generated_at"),
                "counts": source_health.get("counts", {}),
                "stale_threshold_days": source_health.get("stale_threshold_days"),
            }
            if source_health
            else None
        ),
    }


def build_admin_report_csv_text(payload: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["section", "name", "value"])
    for key, value in (payload.get("runs") or {}).items():
        if key not in {"last_successful_pipeline_at", "last_successful_monitor_at"}:
            writer.writerow(["runs", key, value])
    writer.writerow(["runs", "last_successful_pipeline_at", (payload.get("runs") or {}).get("last_successful_pipeline_at") or ""])
    writer.writerow(["runs", "last_successful_monitor_at", (payload.get("runs") or {}).get("last_successful_monitor_at") or ""])
    for key, value in (payload.get("logs") or {}).items():
        writer.writerow(["logs", key, value])
    for key, value in (payload.get("emails") or {}).items():
        if key not in {"recent_campaigns", "team_summary"}:
            writer.writerow(["emails", key, value or ""])
    for key, value in ((payload.get("source_health") or {}).get("counts") or {}).items():
        writer.writerow(["source_health", key, value])

    writer.writerow([])
    writer.writerow(["team_name", "deliveries_total", "deliveries_sent", "deliveries_failed", "latest_sent_at"])
    for item in (payload.get("emails") or {}).get("team_summary", []):
        writer.writerow(
            [
                item.get("team_name"),
                item.get("deliveries_total"),
                item.get("deliveries_sent"),
                item.get("deliveries_failed"),
                item.get("latest_sent_at") or "",
            ]
        )

    writer.writerow([])
    writer.writerow(["campaign_id", "subject", "status", "article_count", "created_at", "sent_at"])
    for item in (payload.get("emails") or {}).get("recent_campaigns", []):
        writer.writerow(
            [
                item.get("id"),
                item.get("subject"),
                item.get("status"),
                item.get("article_count"),
                item.get("created_at") or "",
                item.get("sent_at") or "",
            ]
        )

    return output.getvalue()


@router.get("/runs", response_model=list[JobResponse])
def list_runs(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    items = query.order_by(Job.created_at.desc()).limit(limit).all()
    return [
        JobResponse(
            id=i.id,
            job_type=i.job_type,
            trigger_type=i.trigger_type,
            status=i.status,
            error_message=i.error_message,
            started_at=i.started_at,
            finished_at=i.finished_at,
            created_at=i.created_at,
        )
        for i in items
    ]


@router.get("/runs/{job_id}/sources", response_model=list[JobSourceRunResponse])
def list_run_sources(
    job_id: UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(JobSourceRun, Source.display_name)
        .join(Source, Source.id == JobSourceRun.source_id)
        .filter(JobSourceRun.job_id == job_id)
        .order_by(Source.display_name.asc())
        .all()
    )
    return [
        JobSourceRunResponse(
            id=run.id,
            source_name=source_name,
            status=run.status,
            article_count=run.article_count,
            error_count=run.error_count,
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        for run, source_name in rows
    ]


def _pick_latest_in_window(files: list[Path], started_at, finished_at) -> Path | None:
    if not files:
        return None
    if not started_at:
        return max(files, key=lambda p: p.stat().st_mtime)
    start_ts = started_at.astimezone(UTC).timestamp() - 600
    end_ref = finished_at or started_at
    end_ts = end_ref.astimezone(UTC).timestamp() + 600
    in_window = [p for p in files if start_ts <= p.stat().st_mtime <= end_ts]
    if in_window:
        return max(in_window, key=lambda p: p.stat().st_mtime)
    return max(files, key=lambda p: p.stat().st_mtime)


@router.get("/runs/{job_id}/result")
def get_run_result(
    job_id: UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Run not found.")
    if job.status != "success":
        raise HTTPException(status_code=400, detail="Result is available only for successful runs.")

    articles: list[dict] = []
    result_file: str | None = None

    if job.job_type == "scrape":
        path = DATA_NEWS_DIR / f"admin_run_{str(job.id).replace('-', '')}.json"
        if path.exists():
            result_file = str(path)
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                articles = data[:200]
    elif job.job_type == "pipeline_full":
        candidates = list(DATA_NEWS_DIR.glob("multi_source_news_*.json"))
        picked = _pick_latest_in_window(candidates, job.started_at, job.finished_at)
        if picked and picked.exists():
            result_file = str(picked)
            with picked.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                articles = data[:200]
    elif job.job_type == "html_monitor":
        candidates = list(DATA_MONITORS_DIR.glob("monitor_updates_*.json"))
        picked = _pick_latest_in_window(candidates, job.started_at, job.finished_at)
        if picked and picked.exists():
            result_file = str(picked)
            with picked.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                articles = data[:200]
    elif job.job_type == "source_health":
        candidates = list(DATA_DIAGNOSTICS_DIR.glob("latest_sources_*.json"))
        latest_file = DATA_DIAGNOSTICS_DIR / "latest_source_health.json"
        if latest_file.exists():
            candidates.append(latest_file)
        picked = _pick_latest_in_window(candidates, job.started_at, job.finished_at)
        if picked and picked.exists():
            result_file = str(picked)
            with picked.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                results = data.get("results", []) or []
                if isinstance(results, list):
                    articles = [
                        {
                            "title": item.get("description") or item.get("source_key") or "Source health",
                            "source": item.get("status") or ("error" if item.get("error") else "unknown"),
                            "summary": item.get("status_reason") or item.get("error") or "",
                            "link": "",
                        }
                        for item in results[:200]
                        if isinstance(item, dict)
                    ]

    logs = (
        db.query(AppLog)
        .filter(AppLog.job_id == job.id)
        .order_by(AppLog.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "job_id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "result_file": result_file,
        "article_count": len(articles),
        "articles": articles,
        "logs": [
            {
                "level": log.level,
                "message": log.message,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


@router.get("/logs", response_model=list[AppLogResponse])
def list_logs(
    level: str | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    job_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AppLog, Source.display_name).outerjoin(Source, Source.id == AppLog.source_id)
    if level:
        query = query.filter(AppLog.level == level.upper())
    if source_id:
        query = query.filter(AppLog.source_id == source_id)
    if job_id:
        query = query.filter(AppLog.job_id == job_id)
    if q:
        query = query.filter(AppLog.message.ilike(f"%{q}%"))

    rows = query.order_by(AppLog.created_at.desc()).limit(limit).all()
    return [
        AppLogResponse(
            id=log.id,
            level=log.level,
            message=log.message,
            source_name=source_name,
            job_id=log.job_id,
            created_at=log.created_at,
        )
        for log, source_name in rows
    ]


@router.get("/admin-report")
def get_admin_report(
    days: int = Query(default=7, ge=1, le=30),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_admin_report_payload(days=days, db=db)


@router.get("/admin-report/export.csv")
def export_admin_report_csv(
    days: int = Query(default=7, ge=1, le=30),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = build_admin_report_payload(days=days, db=db)
    data = build_admin_report_csv_text(payload)
    filename = f"admin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/source-health")
def get_source_health(
    _user: User = Depends(get_current_user),
):
    payload = _load_source_health_payload()
    if not payload:
        raise HTTPException(status_code=404, detail="Source health diagnostics not found.")

    return {
        "generated_at": payload.get("generated_at"),
        "recent_days": payload.get("recent_days"),
        "stale_threshold_days": payload.get("stale_threshold_days"),
        "file": payload.get("file"),
        "counts": payload.get("counts", {}),
        "results": payload.get("results", []),
    }
