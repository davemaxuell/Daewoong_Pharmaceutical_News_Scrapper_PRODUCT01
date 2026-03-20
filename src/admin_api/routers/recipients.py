"""Recipient management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models import Recipient, RecipientTeamMap, Team, User
from ..schemas import RecipientCreateRequest, RecipientResponse, RecipientUpdateRequest, TeamResponse


router = APIRouter(prefix="/recipients", tags=["recipients"])


def _get_or_create_team(db: Session, team_name: str) -> Team:
    team = db.query(Team).filter(Team.name == team_name).first()
    if team:
        return team
    team = Team(name=team_name, is_active=True)
    db.add(team)
    db.flush()
    return team


def _set_teams(db: Session, recipient: Recipient, team_names: list[str]) -> None:
    db.query(RecipientTeamMap).filter(RecipientTeamMap.recipient_id == recipient.id).delete()
    unique_team_names = sorted(set([name.strip() for name in team_names if name.strip()]))
    for team_name in unique_team_names:
        team = _get_or_create_team(db, team_name)
        db.add(RecipientTeamMap(recipient_id=recipient.id, team_id=team.id))

    if unique_team_names:
        first_team = db.query(Team).filter(Team.name == unique_team_names[0]).first()
        recipient.team_id = first_team.id if first_team else None
    else:
        recipient.team_id = None


def _recipient_to_response(db: Session, recipient: Recipient) -> RecipientResponse:
    rows = (
        db.query(Team.name)
        .join(RecipientTeamMap, RecipientTeamMap.team_id == Team.id)
        .filter(RecipientTeamMap.recipient_id == recipient.id)
        .all()
    )
    team_names = sorted([name for (name,) in rows])
    return RecipientResponse(
        id=recipient.id,
        email=recipient.email,
        full_name=recipient.full_name,
        is_active=recipient.is_active,
        receives_test_emails=recipient.receives_test_emails,
        team_names=team_names,
        updated_at=recipient.updated_at,
    )


@router.get("/teams", response_model=list[TeamResponse])
def list_teams(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teams = db.query(Team).order_by(Team.name.asc()).all()
    return [TeamResponse(id=t.id, name=t.name) for t in teams]


@router.get("", response_model=list[RecipientResponse])
def list_recipients(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    team_name: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Recipient)
    if q:
        query = query.filter(
            or_(
                Recipient.email.ilike(f"%{q}%"),
                Recipient.full_name.ilike(f"%{q}%"),
            )
        )
    if team_name:
        query = (
            query.join(RecipientTeamMap, RecipientTeamMap.recipient_id == Recipient.id)
            .join(Team, Team.id == RecipientTeamMap.team_id)
            .filter(Team.name == team_name)
            .distinct()
        )
    if is_active is not None:
        query = query.filter(Recipient.is_active.is_(is_active))
    recipients = query.order_by(Recipient.email.asc()).limit(1000).all()
    return [_recipient_to_response(db, item) for item in recipients]


@router.post("", response_model=RecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(
    payload: RecipientCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email = payload.email.lower().strip()
    if db.query(Recipient).filter(Recipient.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recipient already exists")

    recipient = Recipient(
        email=email,
        full_name=payload.full_name,
        is_active=payload.is_active,
        receives_test_emails=payload.receives_test_emails,
    )
    db.add(recipient)
    db.flush()
    _set_teams(db, recipient, payload.team_names)
    db.commit()
    db.refresh(recipient)
    result = _recipient_to_response(db, recipient)
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="recipient.create",
        entity_type="recipient",
        entity_id=str(recipient.id),
        after_json=result.model_dump(),
    )
    db.commit()
    return result


@router.put("/{recipient_id}", response_model=RecipientResponse)
def update_recipient(
    recipient_id: UUID,
    payload: RecipientUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    recipient = db.query(Recipient).filter(Recipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    before = _recipient_to_response(db, recipient).model_dump()

    if payload.full_name is not None:
        recipient.full_name = payload.full_name
    if payload.is_active is not None:
        recipient.is_active = payload.is_active
    if payload.receives_test_emails is not None:
        recipient.receives_test_emails = payload.receives_test_emails
    if payload.team_names is not None:
        _set_teams(db, recipient, payload.team_names)

    db.commit()
    db.refresh(recipient)
    result = _recipient_to_response(db, recipient)
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="recipient.update",
        entity_type="recipient",
        entity_id=str(recipient.id),
        before_json=before,
        after_json=result.model_dump(),
    )
    db.commit()
    return result


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipient(
    recipient_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    recipient = db.query(Recipient).filter(Recipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    before = _recipient_to_response(db, recipient).model_dump()
    db.delete(recipient)
    db.commit()
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="recipient.delete",
        entity_type="recipient",
        entity_id=str(recipient_id),
        before_json=before,
    )
    db.commit()
