"""Email send history routes."""

from __future__ import annotations

from collections import defaultdict
import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import EmailCampaign, EmailDelivery, Recipient, RecipientTeamMap, Team, User
from ..schemas import EmailCampaignDetailResponse, EmailCampaignResponse, EmailDeliveryResponse


router = APIRouter(prefix="/emails", tags=["email-history"])


def _campaign_team_map(db: Session, campaign_ids: list[UUID]) -> dict[UUID, list[str]]:
    if not campaign_ids:
        return {}

    rows = (
        db.query(EmailDelivery.campaign_id, Team.name)
        .join(Recipient, Recipient.id == EmailDelivery.recipient_id, isouter=True)
        .join(RecipientTeamMap, RecipientTeamMap.recipient_id == Recipient.id, isouter=True)
        .join(Team, Team.id == RecipientTeamMap.team_id, isouter=True)
        .filter(EmailDelivery.campaign_id.in_(campaign_ids))
        .filter(Team.name.isnot(None))
        .distinct()
        .all()
    )
    mapping: dict[UUID, set[str]] = defaultdict(set)
    for campaign_id, team_name in rows:
        if campaign_id and team_name:
            mapping[campaign_id].add(team_name)
    return {campaign_id: sorted(names) for campaign_id, names in mapping.items()}


def _delivery_recipient_meta(db: Session, campaign_id: UUID) -> dict[UUID, dict[str, object]]:
    rows = (
        db.query(EmailDelivery.id, Recipient.full_name, Team.name)
        .join(Recipient, Recipient.id == EmailDelivery.recipient_id, isouter=True)
        .join(RecipientTeamMap, RecipientTeamMap.recipient_id == Recipient.id, isouter=True)
        .join(Team, Team.id == RecipientTeamMap.team_id, isouter=True)
        .filter(EmailDelivery.campaign_id == campaign_id)
        .all()
    )
    meta: dict[UUID, dict[str, object]] = {}
    for delivery_id, full_name, team_name in rows:
        current = meta.setdefault(delivery_id, {"full_name": full_name, "team_names": set()})
        if full_name and not current["full_name"]:
            current["full_name"] = full_name
        if team_name:
            current["team_names"].add(team_name)
    return {
        delivery_id: {
            "full_name": value["full_name"],
            "team_names": sorted(value["team_names"]),
        }
        for delivery_id, value in meta.items()
    }


@router.get("/history", response_model=list[EmailCampaignResponse])
def list_email_history(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    team: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EmailCampaign)
    if q:
        query = query.filter(EmailCampaign.subject.ilike(f"%{q}%"))
    if status:
        query = query.filter(EmailCampaign.status == status)
    if team:
        query = (
            query.join(EmailDelivery, EmailDelivery.campaign_id == EmailCampaign.id)
            .join(Recipient, Recipient.id == EmailDelivery.recipient_id, isouter=True)
            .join(RecipientTeamMap, RecipientTeamMap.recipient_id == Recipient.id, isouter=True)
            .join(Team, Team.id == RecipientTeamMap.team_id, isouter=True)
            .filter(Team.name.ilike(f"%{team}%"))
            .distinct()
        )

    items = query.order_by(EmailCampaign.created_at.desc()).limit(limit).all()
    team_map = _campaign_team_map(db, [i.id for i in items])
    return [
        EmailCampaignResponse(
            id=i.id,
            subject=i.subject,
            article_count=i.article_count,
            status=i.status,
            team_names=team_map.get(i.id, []),
            created_at=i.created_at,
            sent_at=i.sent_at,
        )
        for i in items
    ]


@router.get("/history/{campaign_id}", response_model=EmailCampaignDetailResponse)
def get_email_campaign(
    campaign_id: UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not c:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Email campaign not found.")

    ds = (
        db.query(EmailDelivery)
        .filter(EmailDelivery.campaign_id == c.id)
        .order_by(EmailDelivery.created_at.asc())
        .all()
    )
    delivery_meta = _delivery_recipient_meta(db, c.id)
    campaign_team_names = _campaign_team_map(db, [c.id]).get(c.id, [])
    deliveries = [
        EmailDeliveryResponse(
            id=d.id,
            email=d.email,
            full_name=str(delivery_meta.get(d.id, {}).get("full_name") or "") or None,
            team_names=list(delivery_meta.get(d.id, {}).get("team_names") or []),
            delivery_type=d.delivery_type,
            status=d.status,
            error_message=d.error_message,
            sent_at=d.sent_at,
        )
        for d in ds
    ]
    return EmailCampaignDetailResponse(
        id=c.id,
        subject=c.subject,
        body_html=c.body_html,
        body_text=c.body_text,
        article_count=c.article_count,
        status=c.status,
        team_names=campaign_team_names,
        created_at=c.created_at,
        sent_at=c.sent_at,
        deliveries=deliveries,
    )


@router.get("/history/export.csv")
def export_email_history(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    team: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = list_email_history(q=q, status=status, team=team, limit=limit, _user=_user, db=db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["campaign_id", "subject", "status", "article_count", "teams", "created_at", "sent_at"])
    for item in items:
        writer.writerow(
            [
                item.id,
                item.subject,
                item.status,
                item.article_count,
                ", ".join(item.team_names or []),
                item.created_at,
                item.sent_at or "",
            ]
        )

    data = output.getvalue()
    filename = f"email_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
