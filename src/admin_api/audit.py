"""Audit event writer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import AuditEvent


def write_audit(
    db: Session,
    *,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before_json: dict | None = None,
    after_json: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_json,
            after_json=after_json,
        )
    )

