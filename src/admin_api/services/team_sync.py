"""Sync baseline team/category/recipient data from config files."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Category, Recipient, RecipientTeamMap, Team, TeamCategoryMap


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEAM_EMAILS_PATH = PROJECT_ROOT / "config" / "team_emails.json"


def _load_team_payload() -> dict:
    if not TEAM_EMAILS_PATH.exists():
        return {}
    try:
        return json.loads(TEAM_EMAILS_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"[WARN] Failed to load team seed data from {TEAM_EMAILS_PATH}: {exc}")
        return {}


def ensure_team_data_seeded(db: Session) -> None:
    payload = _load_team_payload()
    if not isinstance(payload, dict) or not payload:
        return

    existing_teams = {str(team.name): team for team in db.query(Team).all() if str(team.name or "").strip()}
    existing_categories = {
        str(category.name): category
        for category in db.query(Category).all()
        if str(category.name or "").strip()
    }
    existing_recipients = {
        str(recipient.email).strip().lower(): recipient
        for recipient in db.query(Recipient).all()
        if str(recipient.email or "").strip()
    }

    team_category_map_count = db.query(TeamCategoryMap).count()
    recipient_team_map_count = db.query(RecipientTeamMap).count()

    changed = False
    created_team_names: set[str] = set()

    for team_key, raw_team_info in payload.items():
        team_info = raw_team_info if isinstance(raw_team_info, dict) else {}
        team_name = str(team_info.get("team_name") or team_key or "").strip()
        if not team_name:
            continue

        team = existing_teams.get(team_name)
        if team is None:
            team = Team(
                name=team_name,
                description="Seeded from config/team_emails.json",
                is_active=True,
            )
            db.add(team)
            db.flush()
            existing_teams[team_name] = team
            created_team_names.add(team_name)
            changed = True
        elif team.is_active is not True:
            team.is_active = True
            changed = True

        should_seed_team_categories = team_name in created_team_names or team_category_map_count == 0
        if should_seed_team_categories:
            for raw_category in team_info.get("categories", []) or []:
                category_name = str(raw_category or "").strip()
                if not category_name:
                    continue

                category = existing_categories.get(category_name)
                if category is None:
                    category = Category(name=category_name, is_active=True)
                    db.add(category)
                    db.flush()
                    existing_categories[category_name] = category
                    changed = True
                elif category.is_active is not True:
                    category.is_active = True
                    changed = True

                exists = (
                    db.query(TeamCategoryMap)
                    .filter(
                        TeamCategoryMap.team_id == team.id,
                        TeamCategoryMap.category_id == category.id,
                    )
                    .first()
                )
                if exists is None:
                    db.add(TeamCategoryMap(team_id=team.id, category_id=category.id))
                    changed = True

        should_seed_team_members = team_name in created_team_names or recipient_team_map_count == 0
        if should_seed_team_members:
            for raw_member in team_info.get("members", []) or []:
                member = raw_member if isinstance(raw_member, dict) else {}
                email = str(member.get("email") or "").strip().lower()
                if not email:
                    continue

                full_name = str(member.get("name") or "").strip() or None
                recipient = existing_recipients.get(email)
                if recipient is None:
                    recipient = Recipient(
                        email=email,
                        full_name=full_name,
                        team_id=team.id,
                        is_active=True,
                    )
                    db.add(recipient)
                    db.flush()
                    existing_recipients[email] = recipient
                    changed = True
                else:
                    if full_name and not recipient.full_name:
                        recipient.full_name = full_name
                        changed = True
                    if recipient.team_id is None:
                        recipient.team_id = team.id
                        changed = True
                    if recipient.is_active is not True:
                        recipient.is_active = True
                        changed = True

                membership_exists = (
                    db.query(RecipientTeamMap)
                    .filter(
                        RecipientTeamMap.recipient_id == recipient.id,
                        RecipientTeamMap.team_id == team.id,
                    )
                    .first()
                )
                if membership_exists is None:
                    db.add(RecipientTeamMap(recipient_id=recipient.id, team_id=team.id))
                    changed = True

    if changed:
        db.commit()
