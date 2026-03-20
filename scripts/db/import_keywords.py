"""Import categories and keywords from src/keywords.py into PostgreSQL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from db_common import get_database_url, normalize_keyword, postgres_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.keywords import KEYWORDS  # type: ignore  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", help="PostgreSQL connection URL")
    parser.add_argument("--language-code", default="ko", help="Language code for keywords")
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


def upsert_keyword(cur, keyword: str, language_code: str) -> str:
    normalized = normalize_keyword(keyword)
    cur.execute(
        """
        INSERT INTO keywords (keyword, normalized_keyword, language_code, is_active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (normalized_keyword, language_code)
        DO UPDATE SET keyword = EXCLUDED.keyword, is_active = TRUE, updated_at = NOW()
        RETURNING id
        """,
        (keyword, normalized, language_code),
    )
    return cur.fetchone()[0]


def map_keyword_to_category(cur, keyword_id: str, category_id: str) -> None:
    cur.execute(
        """
        INSERT INTO keyword_category_map (keyword_id, category_id)
        VALUES (%s, %s)
        ON CONFLICT (keyword_id, category_id)
        DO NOTHING
        """,
        (keyword_id, category_id),
    )


def run(db_url: str, language_code: str, dry_run: bool) -> None:
    category_count = 0
    keyword_count = 0
    mapping_count = 0

    with postgres_connection(db_url) as conn:
        with conn.cursor() as cur:
            for category, keywords in KEYWORDS.items():
                category_id = upsert_category(cur, category)
                category_count += 1

                seen_normalized: set[str] = set()
                for keyword in keywords:
                    if not keyword or not keyword.strip():
                        continue

                    normalized = normalize_keyword(keyword)
                    if normalized in seen_normalized:
                        continue
                    seen_normalized.add(normalized)

                    keyword_id = upsert_keyword(cur, keyword.strip(), language_code)
                    keyword_count += 1
                    map_keyword_to_category(cur, keyword_id, category_id)
                    mapping_count += 1

        if dry_run:
            conn.rollback()
            print("[DRY-RUN] Rolled back transaction.")
        else:
            conn.commit()

    print(f"Categories processed: {category_count}")
    print(f"Keywords processed: {keyword_count}")
    print(f"Keyword-category mappings processed: {mapping_count}")


def main() -> int:
    args = build_parser().parse_args()
    db_url = get_database_url(args.db_url)
    run(db_url=db_url, language_code=args.language_code, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

