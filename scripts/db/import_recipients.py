"""Import teams and recipients from config/team_emails.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from db_common import get_database_url, postgres_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEAM_EMAILS = PROJECT_ROOT / "config" / "team_emails.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--team-emails",
        default=str(DEFAULT_TEAM_EMAILS),
        help="Path to team email JSON file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without commit")
    return parser


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def upsert_team(cur, team_name: str) -> str:
    cur.execute(
        """
        INSERT INTO teams (name, is_active)
        VALUES (%s, TRUE)
        ON CONFLICT (name)
        DO UPDATE SET is_active = TRUE, updated_at = NOW()
        RETURNING id
        """,
        (team_name,),
    )
    return cur.fetchone()[0]


def upsert_category(cur, category_name: str) -> str:
    cur.execute(
        """
        INSERT INTO categories (name, is_active)
        VALUES (%s, TRUE)
        ON CONFLICT (name)
        DO UPDATE SET is_active = TRUE, updated_at = NOW()
        RETURNING id
        """,
        (category_name,),
    )
    return cur.fetchone()[0]


def map_team_category(cur, team_id: str, category_id: str) -> None:
    cur.execute(
        """
        INSERT INTO team_category_map (team_id, category_id)
        VALUES (%s, %s)
        ON CONFLICT (team_id, category_id)
        DO NOTHING
        """,
        (team_id, category_id),
    )


def upsert_recipient(cur, email: str, full_name: str | None, team_id: str) -> str:
    cur.execute(
        """
        INSERT INTO recipients (email, full_name, team_id, is_active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (email)
        DO UPDATE SET
            full_name = EXCLUDED.full_name,
            team_id = COALESCE(recipients.team_id, EXCLUDED.team_id),
            is_active = TRUE,
            updated_at = NOW()
        RETURNING id
        """,
        (email, full_name, team_id),
    )
    return cur.fetchone()[0]


def map_recipient_team(cur, recipient_id: str, team_id: str) -> None:
    cur.execute(
        """
        INSERT INTO recipient_team_map (recipient_id, team_id)
        VALUES (%s, %s)
        ON CONFLICT (recipient_id, team_id)
        DO NOTHING
        """,
        (recipient_id, team_id),
    )


def run(db_url: str, team_emails_path: Path, dry_run: bool) -> None:
    payload = load_json(team_emails_path)
    team_count = 0
    recipient_count = 0
    membership_count = 0

    with postgres_connection(db_url) as conn:
        with conn.cursor() as cur:
            for team_key, team_info in payload.items():
                team_name = (team_info.get("team_name") or team_key).strip()
                if not team_name:
                    continue

                team_id = upsert_team(cur, team_name)
                team_count += 1

                for category in team_info.get("categories", []):
                    if not category or not category.strip():
                        continue
                    category_id = upsert_category(cur, category.strip())
                    map_team_category(cur, team_id, category_id)

                for member in team_info.get("members", []):
                    email = (member.get("email") or "").strip().lower()
                    if not email:
                        continue

                    name = (member.get("name") or "").strip() or None
                    recipient_id = upsert_recipient(cur, email=email, full_name=name, team_id=team_id)
                    recipient_count += 1

                    map_recipient_team(cur, recipient_id, team_id)
                    membership_count += 1

        if dry_run:
            conn.rollback()
            print("[DRY-RUN] Rolled back transaction.")
        else:
            conn.commit()

    print(f"Teams processed: {team_count}")
    print(f"Recipients processed: {recipient_count}")
    print(f"Recipient-team mappings processed: {membership_count}")


def main() -> int:
    args = build_parser().parse_args()
    db_url = get_database_url(args.db_url)
    team_emails_path = Path(args.team_emails).resolve()
    run(db_url=db_url, team_emails_path=team_emails_path, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

