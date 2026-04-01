"""Recipient management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models import (
    Category,
    EmailDelivery,
    Keyword,
    KeywordCategoryMap,
    Recipient,
    RecipientTeamMap,
    Team,
    TeamCategoryMap,
    User,
)
from ..schemas import (
    RecipientCreateRequest,
    RecipientResponse,
    RecipientUpdateRequest,
    TeamCategoryUpdateRequest,
    TeamResponse,
    TeamRoutingResponse,
)
from ..services.keyword_sync import ensure_keywords_seeded
from ..services.team_sync import ensure_team_data_seeded


router = APIRouter(prefix="/recipients", tags=["recipients"])


def _get_or_create_team(db: Session, team_name: str) -> Team:
    team = db.query(Team).filter(Team.name == team_name).first()
    if team:
        return team
    team = Team(name=team_name, is_active=True)
    db.add(team)
    db.flush()
    return team


def _get_or_create_category(db: Session, category_name: str) -> Category:
    category = db.query(Category).filter(Category.name == category_name).first()
    if category:
        return category
    category = Category(name=category_name, is_active=True)
    db.add(category)
    db.flush()
    return category


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


def _set_team_categories(db: Session, team: Team, category_names: list[str]) -> None:
    db.query(TeamCategoryMap).filter(TeamCategoryMap.team_id == team.id).delete()
    unique_category_names = sorted(set([name.strip() for name in category_names if name.strip()]))
    for category_name in unique_category_names:
        category = _get_or_create_category(db, category_name)
        db.add(TeamCategoryMap(team_id=team.id, category_id=category.id))


def _delete_recipient_dependencies(db: Session, recipient_id: UUID) -> None:
    db.query(RecipientTeamMap).filter(RecipientTeamMap.recipient_id == recipient_id).delete(
        synchronize_session=False
    )
    db.query(EmailDelivery).filter(EmailDelivery.recipient_id == recipient_id).update(
        {EmailDelivery.recipient_id: None},
        synchronize_session=False,
    )


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


def _team_to_routing_response(db: Session, team: Team) -> TeamRoutingResponse:
    category_rows = (
        db.query(Category.name)
        .join(TeamCategoryMap, TeamCategoryMap.category_id == Category.id)
        .filter(
            TeamCategoryMap.team_id == team.id,
            Category.is_active.is_(True),
        )
        .order_by(Category.name.asc())
        .all()
    )
    keyword_rows = (
        db.query(Keyword.keyword, Keyword.normalized_keyword)
        .join(KeywordCategoryMap, KeywordCategoryMap.keyword_id == Keyword.id)
        .join(Category, Category.id == KeywordCategoryMap.category_id)
        .join(TeamCategoryMap, TeamCategoryMap.category_id == Category.id)
        .filter(
            TeamCategoryMap.team_id == team.id,
            Category.is_active.is_(True),
            Keyword.is_active.is_(True),
        )
        .order_by(Keyword.keyword.asc())
        .all()
    )
    keyword_names: list[str] = []
    seen_keywords: set[str] = set()
    for keyword_value, normalized_value in keyword_rows:
        keyword_text = str(keyword_value or "").strip()
        normalized_text = str(normalized_value or "").strip() or keyword_text.casefold()
        if not keyword_text or normalized_text in seen_keywords:
            continue
        seen_keywords.add(normalized_text)
        keyword_names.append(keyword_text)

    recipient_count = (
        db.query(func.count(func.distinct(Recipient.id)))
        .join(RecipientTeamMap, RecipientTeamMap.recipient_id == Recipient.id)
        .filter(
            RecipientTeamMap.team_id == team.id,
            Recipient.is_active.is_(True),
        )
        .scalar()
        or 0
    )
    return TeamRoutingResponse(
        id=team.id,
        name=team.name,
        is_active=team.is_active,
        category_names=[name for (name,) in category_rows],
        recipient_count=int(recipient_count),
        keyword_count=len(keyword_names),
        keywords=keyword_names,
    )


@router.get("/teams", response_model=list[TeamResponse])
def list_teams(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_team_data_seeded(db)
    teams = db.query(Team).order_by(Team.name.asc()).all()
    return [TeamResponse(id=t.id, name=t.name) for t in teams]


@router.get("/team-routing", response_model=list[TeamRoutingResponse])
def list_team_routing(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_team_data_seeded(db)
    ensure_keywords_seeded(db)
    teams = db.query(Team).order_by(Team.name.asc()).all()
    return [_team_to_routing_response(db, team) for team in teams]


@router.put("/teams/{team_id}/routing", response_model=TeamRoutingResponse)
def update_team_routing(
    team_id: UUID,
    payload: TeamCategoryUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    before = _team_to_routing_response(db, team).model_dump()
    _set_team_categories(db, team, payload.category_names)
    db.commit()
    db.refresh(team)

    result = _team_to_routing_response(db, team)
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="team.routing.update",
        entity_type="team",
        entity_id=str(team.id),
        before_json=before,
        after_json=result.model_dump(),
    )
    db.commit()
    return result


@router.get("", response_model=list[RecipientResponse])
def list_recipients(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    team_name: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_team_data_seeded(db)
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
    _delete_recipient_dependencies(db, recipient.id)
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
