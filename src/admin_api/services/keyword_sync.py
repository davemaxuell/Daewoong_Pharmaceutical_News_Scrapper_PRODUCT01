"""Seed admin keyword tables from the managed keyword source when empty."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Category, Keyword, KeywordCategoryMap


def _normalize_keyword(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def ensure_keywords_seeded(db: Session) -> None:
    active_keyword_count = db.query(Keyword).filter(Keyword.is_active.is_(True)).count()
    if active_keyword_count > 0:
        return

    from src.keywords import KEYWORDS

    categories_by_name = {str(category.name): category for category in db.query(Category).all()}
    changed = False

    for category_name, keywords in KEYWORDS.items():
        category = categories_by_name.get(category_name)
        if category is None:
            category = Category(name=category_name, is_active=True)
            db.add(category)
            db.flush()
            categories_by_name[category_name] = category
            changed = True
        elif category.is_active is not True:
            category.is_active = True
            changed = True

        seen_normalized: set[str] = set()
        for raw_keyword in keywords:
            keyword_value = str(raw_keyword or "").strip()
            if not keyword_value:
                continue

            normalized_keyword = _normalize_keyword(keyword_value)
            if normalized_keyword in seen_normalized:
                continue
            seen_normalized.add(normalized_keyword)

            keyword = (
                db.query(Keyword)
                .filter(
                    Keyword.normalized_keyword == normalized_keyword,
                    Keyword.language_code == "ko",
                )
                .first()
            )
            if keyword is None:
                keyword = Keyword(
                    keyword=keyword_value,
                    normalized_keyword=normalized_keyword,
                    language_code="ko",
                    is_active=True,
                )
                db.add(keyword)
                db.flush()
                changed = True
            else:
                if keyword.keyword != keyword_value:
                    keyword.keyword = keyword_value
                    changed = True
                if keyword.is_active is not True:
                    keyword.is_active = True
                    changed = True

            mapping_exists = (
                db.query(KeywordCategoryMap)
                .filter(
                    KeywordCategoryMap.keyword_id == keyword.id,
                    KeywordCategoryMap.category_id == category.id,
                )
                .first()
            )
            if mapping_exists is None:
                db.add(KeywordCategoryMap(keyword_id=keyword.id, category_id=category.id))
                changed = True

    if changed:
        db.commit()
