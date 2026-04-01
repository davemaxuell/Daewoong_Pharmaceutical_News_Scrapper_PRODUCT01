"""Keyword management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models import Category, Keyword, KeywordCategoryMap, User
from ..schemas import KeywordCreateRequest, KeywordResponse, KeywordUpdateRequest
from ..services.keyword_sync import ensure_keywords_seeded
from ..services.team_sync import ensure_team_data_seeded


router = APIRouter(prefix="/keywords", tags=["keywords"])


def _normalize_keyword(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _get_or_create_category(db: Session, name: str) -> Category:
    category = db.query(Category).filter(Category.name == name).first()
    if category:
        return category
    category = Category(name=name, is_active=True)
    db.add(category)
    db.flush()
    return category


def _keyword_to_response(db: Session, keyword: Keyword) -> KeywordResponse:
    rows = (
        db.query(Category.name)
        .join(KeywordCategoryMap, KeywordCategoryMap.category_id == Category.id)
        .filter(KeywordCategoryMap.keyword_id == keyword.id)
        .all()
    )
    categories = sorted([name for (name,) in rows])
    return KeywordResponse(
        id=keyword.id,
        keyword=keyword.keyword,
        normalized_keyword=keyword.normalized_keyword,
        language_code=keyword.language_code,
        is_active=keyword.is_active,
        categories=categories,
        updated_at=keyword.updated_at,
    )


def _delete_keyword_dependencies(db: Session, keyword_id: UUID) -> None:
    db.query(KeywordCategoryMap).filter(KeywordCategoryMap.keyword_id == keyword_id).delete(
        synchronize_session=False
    )


@router.get("", response_model=list[KeywordResponse])
def list_keywords(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    group: str | None = Query(default=None),
    language_code: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_keywords_seeded(db)
    query = db.query(Keyword)
    if group:
        query = (
            query.join(KeywordCategoryMap, KeywordCategoryMap.keyword_id == Keyword.id)
            .join(Category, Category.id == KeywordCategoryMap.category_id)
            .filter(Category.name == group)
            .distinct()
        )
    if q:
        query = query.filter(Keyword.keyword.ilike(f"%{q}%"))
    if language_code:
        query = query.filter(Keyword.language_code == language_code.strip())
    if is_active is not None:
        query = query.filter(Keyword.is_active.is_(is_active))
    items = query.order_by(Keyword.keyword.asc()).limit(500).all()
    return [_keyword_to_response(db, item) for item in items]


@router.get("/groups", response_model=list[str])
def list_keyword_groups(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_team_data_seeded(db)
    ensure_keywords_seeded(db)
    rows = (
        db.query(Category.name)
        .filter(Category.is_active.is_(True))
        .order_by(Category.name.asc())
        .all()
    )
    return [name for (name,) in rows]


@router.get("/languages", response_model=list[str])
def list_keyword_languages(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_keywords_seeded(db)
    rows = (
        db.query(Keyword.language_code)
        .filter(Keyword.language_code.isnot(None), Keyword.language_code != "")
        .distinct()
        .order_by(Keyword.language_code.asc())
        .all()
    )
    return [language_code for (language_code,) in rows]


@router.post("", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def create_keyword(
    payload: KeywordCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    normalized = _normalize_keyword(payload.keyword)
    exists = (
        db.query(Keyword)
        .filter(
            and_(
                Keyword.normalized_keyword == normalized,
                Keyword.language_code == payload.language_code,
            )
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keyword already exists")

    keyword = Keyword(
        keyword=payload.keyword.strip(),
        normalized_keyword=normalized,
        language_code=payload.language_code,
        is_active=payload.is_active,
    )
    db.add(keyword)
    db.flush()

    for category_name in sorted(set([c.strip() for c in payload.category_names if c.strip()])):
        category = _get_or_create_category(db, category_name)
        db.add(KeywordCategoryMap(keyword_id=keyword.id, category_id=category.id))

    db.commit()
    db.refresh(keyword)
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="keyword.create",
        entity_type="keyword",
        entity_id=str(keyword.id),
        after_json={
            "keyword": keyword.keyword,
            "language_code": keyword.language_code,
            "is_active": keyword.is_active,
            "categories": payload.category_names,
        },
    )
    db.commit()
    return _keyword_to_response(db, keyword)


@router.put("/{keyword_id}", response_model=KeywordResponse)
def update_keyword(
    keyword_id: UUID,
    payload: KeywordUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")

    before = _keyword_to_response(db, keyword).model_dump()

    if payload.keyword is not None:
        keyword.keyword = payload.keyword.strip()
        keyword.normalized_keyword = _normalize_keyword(payload.keyword)
    if payload.language_code is not None:
        keyword.language_code = payload.language_code
    if payload.is_active is not None:
        keyword.is_active = payload.is_active

    if payload.category_names is not None:
        db.query(KeywordCategoryMap).filter(KeywordCategoryMap.keyword_id == keyword.id).delete()
        for category_name in sorted(set([c.strip() for c in payload.category_names if c.strip()])):
            category = _get_or_create_category(db, category_name)
            db.add(KeywordCategoryMap(keyword_id=keyword.id, category_id=category.id))

    db.commit()
    db.refresh(keyword)
    after = _keyword_to_response(db, keyword)
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="keyword.update",
        entity_type="keyword",
        entity_id=str(keyword.id),
        before_json=before,
        after_json=after.model_dump(),
    )
    db.commit()
    return after


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(
    keyword_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    before = _keyword_to_response(db, keyword).model_dump()
    _delete_keyword_dependencies(db, keyword.id)
    db.delete(keyword)
    db.commit()
    write_audit(
        db,
        actor_user_id=str(admin.id),
        action="keyword.delete",
        entity_type="keyword",
        entity_id=str(keyword_id),
        before_json=before,
    )
    db.commit()
