"""Import teams and team-category mappings from src/team_definitions.py."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from db_common import get_database_url, postgres_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.team_definitions import TEAM_DEFINITIONS  # type: ignore  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", help="PostgreSQL connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Preview without commit")
    return parser


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


def upsert_team(cur, team_name: str, description: str | None) -> str:
    cur.execute(
        """
        INSERT INTO teams (name, description, is_active)
        VALUES (%s, %s, TRUE)
        ON CONFLICT (name)
        DO UPDATE SET
            description = EXCLUDED.description,
            is_active = TRUE,
            updated_at = NOW()
        RETURNING id
        """,
        (team_name, description),
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


def run(db_url: str, dry_run: bool) -> None:
    team_count = 0
    category_count = 0
    mapping_count = 0

    with postgres_connection(db_url) as conn:
        with conn.cursor() as cur:
            for team_name, team_info in TEAM_DEFINITIONS.items():
                team_id = upsert_team(cur, team_name, team_info.get("description"))
                team_count += 1

                for category in team_info.get("categories", []):
                    if not category or not category.strip():
                        continue
                    category_id = upsert_category(cur, category.strip())
                    category_count += 1
                    map_team_category(cur, team_id, category_id)
                    mapping_count += 1

        if dry_run:
            conn.rollback()
            print("[DRY-RUN] Rolled back transaction.")
        else:
            conn.commit()

    print(f"Teams processed: {team_count}")
    print(f"Team categories processed: {category_count}")
    print(f"Team-category mappings processed: {mapping_count}")


def main() -> int:
    args = build_parser().parse_args()
    db_url = get_database_url(args.db_url)
    run(db_url=db_url, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

