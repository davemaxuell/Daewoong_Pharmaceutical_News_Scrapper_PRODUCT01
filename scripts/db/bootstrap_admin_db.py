"""Bootstrap admin DB: apply schema and run import scripts in order."""

from __future__ import annotations

import argparse
from pathlib import Path

from db_common import get_database_url, postgres_connection
from import_keywords import run as run_keywords
from import_recipients import run as run_recipients
from import_teams import run as run_teams


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_FILE = PROJECT_ROOT / "docs" / "admin_db_schema_v1.sql"
DEFAULT_TEAM_EMAILS = PROJECT_ROOT / "config" / "team_emails.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--schema-file",
        default=str(DEFAULT_SCHEMA_FILE),
        help="Path to SQL schema file",
    )
    parser.add_argument(
        "--team-emails",
        default=str(DEFAULT_TEAM_EMAILS),
        help="Path to team email JSON file",
    )
    parser.add_argument("--language-code", default="ko", help="Language code for keywords")
    parser.add_argument("--dry-run", action="store_true", help="Dry run imports (no commit)")
    parser.add_argument("--skip-schema", action="store_true", help="Skip schema apply step")
    parser.add_argument("--skip-keywords", action="store_true", help="Skip keyword import step")
    parser.add_argument("--skip-teams", action="store_true", help="Skip team import step")
    parser.add_argument("--skip-recipients", action="store_true", help="Skip recipient import step")
    return parser


def split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    n = len(sql_text)

    while i < n:
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < n else ""

        # Skip line comments
        if not in_single_quote and not in_double_quote and ch == "-" and nxt == "-":
            while i < n and sql_text[i] != "\n":
                i += 1
            continue

        if ch == "'" and not in_double_quote:
            if in_single_quote and nxt == "'":
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            in_single_quote = not in_single_quote
            buf.append(ch)
            i += 1
            continue

        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            buf.append(ch)
            i += 1
            continue

        if ch == ";" and not in_single_quote and not in_double_quote:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf.clear()
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)

    return statements


def apply_schema(db_url: str, schema_file: Path) -> None:
    sql_text = schema_file.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    if not statements:
        raise ValueError(f"No SQL statements found in {schema_file}")

    with postgres_connection(db_url) as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()

    print(f"Applied schema statements: {len(statements)}")


def main() -> int:
    args = build_parser().parse_args()
    db_url = get_database_url(args.db_url)
    schema_file = Path(args.schema_file).resolve()
    team_emails_path = Path(args.team_emails).resolve()

    if args.dry_run and not args.skip_schema:
        print("[INFO] --dry-run is set: schema apply skipped automatically.")
        args.skip_schema = True

    if not args.skip_schema:
        print(f"[STEP] Applying schema: {schema_file}")
        apply_schema(db_url=db_url, schema_file=schema_file)
    else:
        print("[STEP] Skipping schema apply.")

    if not args.skip_keywords:
        print("[STEP] Importing keywords...")
        run_keywords(db_url=db_url, language_code=args.language_code, dry_run=args.dry_run)
    else:
        print("[STEP] Skipping keyword import.")

    if not args.skip_teams:
        print("[STEP] Importing teams...")
        run_teams(db_url=db_url, dry_run=args.dry_run)
    else:
        print("[STEP] Skipping team import.")

    if not args.skip_recipients:
        print("[STEP] Importing recipients...")
        run_recipients(db_url=db_url, team_emails_path=team_emails_path, dry_run=args.dry_run)
    else:
        print("[STEP] Skipping recipient import.")

    print("[DONE] Bootstrap completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

