"""Settings endpoints: sources + general + schedule."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models import Schedule, Setting, Source, User
from ..schemas import (
    GeneralSettingsResponse,
    GeneralSettingsUpdateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
    SettingsOverviewResponse,
    SourceSettingResponse,
    SourceSettingUpdateRequest,
)
from ..services.source_sync import ensure_sources_seeded


router = APIRouter(prefix="/settings", tags=["settings"])
DEFAULT_SCRAPE_FREQUENCY_MINUTES = 1440
DEFAULT_MAX_TOTAL_ARTICLES = 2000
DEFAULT_SCHEDULE_CRON = "0 8 * * *"
DEFAULT_SCHEDULE_TIMEZONE = "Asia/Seoul"
DEFAULT_SOURCE_TIMEOUT_SECONDS = 120
DEFAULT_SOURCE_MAX_ITEMS = 200


def _get_int_setting(db: Session, key: str, default_value: int) -> int:
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row:
        db.add(Setting(key=key, value_json={"value": default_value}))
        db.commit()
        return default_value
    return int(row.value_json.get("value", default_value))


def _set_int_setting(db: Session, key: str, value: int, updated_by: UUID) -> None:
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row:
        row = Setting(key=key, value_json={"value": value}, updated_by=updated_by)
        db.add(row)
    else:
        row.value_json = {"value": value}
        row.updated_by = updated_by
    db.commit()


def _get_or_create_default_schedule(db: Session) -> Schedule:
    row = db.query(Schedule).filter(Schedule.name == "default-daily").first()
    if row:
        return row
    row = Schedule(
        name="default-daily",
        cron_expr=DEFAULT_SCHEDULE_CRON,
        timezone=DEFAULT_SCHEDULE_TIMEZONE,
        is_enabled=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/overview", response_model=SettingsOverviewResponse)
def settings_overview(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_sources_seeded(db)
    sources = db.query(Source).order_by(Source.code.asc()).all()
    frequency = _get_int_setting(db, "scrape.default_frequency_minutes", DEFAULT_SCRAPE_FREQUENCY_MINUTES)
    max_articles = _get_int_setting(db, "scrape.max_total_articles", DEFAULT_MAX_TOTAL_ARTICLES)
    schedule = _get_or_create_default_schedule(db)

    return SettingsOverviewResponse(
        sources=[
            SourceSettingResponse(
                id=s.id,
                code=s.code,
                display_name=s.display_name,
                scraper_module=s.scraper_module,
                is_enabled=s.is_enabled,
                timeout_seconds=s.timeout_seconds,
                max_items=s.max_items,
            )
            for s in sources
        ],
        general=GeneralSettingsResponse(
            scrape_frequency_minutes=frequency,
            max_total_articles=max_articles,
        ),
        schedule=ScheduleResponse(
            id=schedule.id,
            name=schedule.name,
            cron_expr=schedule.cron_expr,
            timezone=schedule.timezone,
            is_enabled=schedule.is_enabled,
        ),
    )


@router.put("/sources/{source_id}", response_model=SourceSettingResponse)
def update_source(
    source_id: UUID,
    payload: SourceSettingUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    before = {
        "is_enabled": source.is_enabled,
        "timeout_seconds": source.timeout_seconds,
        "max_items": source.max_items,
    }
    if payload.is_enabled is not None:
        source.is_enabled = payload.is_enabled
    if payload.timeout_seconds is not None:
        source.timeout_seconds = payload.timeout_seconds
    if payload.max_items is not None:
        source.max_items = payload.max_items
    db.commit()
    db.refresh(source)

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="settings.source.update",
        entity_type="source",
        entity_id=str(source.id),
        before_json=before,
        after_json={
            "is_enabled": source.is_enabled,
            "timeout_seconds": source.timeout_seconds,
            "max_items": source.max_items,
        },
    )
    db.commit()

    return SourceSettingResponse(
        id=source.id,
        code=source.code,
        display_name=source.display_name,
        scraper_module=source.scraper_module,
        is_enabled=source.is_enabled,
        timeout_seconds=source.timeout_seconds,
        max_items=source.max_items,
    )


@router.put("/general", response_model=GeneralSettingsResponse)
def update_general(
    payload: GeneralSettingsUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    before = {
        "scrape_frequency_minutes": _get_int_setting(db, "scrape.default_frequency_minutes", DEFAULT_SCRAPE_FREQUENCY_MINUTES),
        "max_total_articles": _get_int_setting(db, "scrape.max_total_articles", DEFAULT_MAX_TOTAL_ARTICLES),
    }
    _set_int_setting(
        db,
        "scrape.default_frequency_minutes",
        payload.scrape_frequency_minutes,
        admin.id,
    )
    _set_int_setting(
        db,
        "scrape.max_total_articles",
        payload.max_total_articles,
        admin.id,
    )

    after = {
        "scrape_frequency_minutes": payload.scrape_frequency_minutes,
        "max_total_articles": payload.max_total_articles,
    }
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="settings.general.update",
        entity_type="settings",
        entity_id="general",
        before_json=before,
        after_json=after,
    )
    db.commit()
    return GeneralSettingsResponse(**after)


@router.put("/schedule/default", response_model=ScheduleResponse)
def update_schedule(
    payload: ScheduleUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = _get_or_create_default_schedule(db)
    before = {
        "cron_expr": row.cron_expr,
        "timezone": row.timezone,
        "is_enabled": row.is_enabled,
    }

    row.cron_expr = payload.cron_expr
    row.timezone = payload.timezone
    row.is_enabled = payload.is_enabled
    row.updated_by = admin.id
    db.commit()
    db.refresh(row)

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="settings.schedule.update",
        entity_type="schedule",
        entity_id=str(row.id),
        before_json=before,
        after_json={
            "cron_expr": row.cron_expr,
            "timezone": row.timezone,
            "is_enabled": row.is_enabled,
        },
    )
    db.commit()
    return ScheduleResponse(
        id=row.id,
        name=row.name,
        cron_expr=row.cron_expr,
        timezone=row.timezone,
        is_enabled=row.is_enabled,
    )


@router.post("/reset-defaults", response_model=SettingsOverviewResponse)
def reset_defaults(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_sources_seeded(db)
    before = {
        "general": {
            "scrape_frequency_minutes": _get_int_setting(
                db, "scrape.default_frequency_minutes", DEFAULT_SCRAPE_FREQUENCY_MINUTES
            ),
            "max_total_articles": _get_int_setting(db, "scrape.max_total_articles", DEFAULT_MAX_TOTAL_ARTICLES),
        },
        "schedule": {},
        "sources": [],
    }

    schedule = _get_or_create_default_schedule(db)
    before["schedule"] = {
        "cron_expr": schedule.cron_expr,
        "timezone": schedule.timezone,
        "is_enabled": schedule.is_enabled,
    }

    from src.multi_source_scraper import MultiSourceScraper

    scraper = MultiSourceScraper()
    sources = db.query(Source).order_by(Source.code.asc()).all()
    for source in sources:
        before["sources"].append(
            {
                "code": source.code,
                "is_enabled": source.is_enabled,
                "timeout_seconds": source.timeout_seconds,
                "max_items": source.max_items,
            }
        )
        config = scraper.scrapers_config.get(source.code, {})
        source.is_enabled = bool(config.get("enabled", True))
        source.timeout_seconds = DEFAULT_SOURCE_TIMEOUT_SECONDS
        source.max_items = DEFAULT_SOURCE_MAX_ITEMS

    _set_int_setting(
        db,
        "scrape.default_frequency_minutes",
        DEFAULT_SCRAPE_FREQUENCY_MINUTES,
        admin.id,
    )
    _set_int_setting(
        db,
        "scrape.max_total_articles",
        DEFAULT_MAX_TOTAL_ARTICLES,
        admin.id,
    )

    schedule.cron_expr = DEFAULT_SCHEDULE_CRON
    schedule.timezone = DEFAULT_SCHEDULE_TIMEZONE
    schedule.is_enabled = True
    schedule.updated_by = admin.id
    db.commit()

    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="settings.reset_defaults",
        entity_type="settings",
        entity_id="system-base",
        before_json=before,
        after_json={
            "general": {
                "scrape_frequency_minutes": DEFAULT_SCRAPE_FREQUENCY_MINUTES,
                "max_total_articles": DEFAULT_MAX_TOTAL_ARTICLES,
            },
            "schedule": {
                "cron_expr": DEFAULT_SCHEDULE_CRON,
                "timezone": DEFAULT_SCHEDULE_TIMEZONE,
                "is_enabled": True,
            },
            "sources_reset": len(sources),
        },
    )
    db.commit()
    return settings_overview(_user=admin, db=db)
