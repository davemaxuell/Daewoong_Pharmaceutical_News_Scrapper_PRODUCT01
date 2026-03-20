# Admin DB Schema v1 Guide

## Files
- SQL schema: `docs/admin_db_schema_v1.sql`
- Import scripts:
  - `scripts/db/bootstrap_admin_db.py`
  - `scripts/db/import_keywords.py`
  - `scripts/db/import_teams.py`
  - `scripts/db/import_recipients.py`

## What this schema covers
- Login and RBAC: `users`, `roles`, `user_roles`
- Keyword management: `keywords`, `categories`, `keyword_category_map`
- Recipient management: `teams`, `team_category_map`, `recipients`, `recipient_team_map`
- Scraper control and settings: `sources`, `settings`, `schedules`
- Run monitor: `jobs`, `job_source_runs`
- Log viewer: `app_logs`
- Email preview/history: `email_campaigns`, `email_deliveries`
- Change history: `audit_events`

## Migration order (recommended)
1. Create DB and run `docs/admin_db_schema_v1.sql`.
2. Seed `sources` with your existing scrapers.
3. Import existing keywords from `src/keywords.py` into `categories/keywords/keyword_category_map`.
4. Import team mappings from `src/team_definitions.py` into `teams/team_category_map`.
5. Import current recipient list into `recipients`.
6. Wire scraper runs to write into `jobs` + `job_source_runs`.
7. Wire app logging to write into `app_logs` (or ship from file logs).
8. Wire email sender to create `email_campaigns` + `email_deliveries`.
9. Add audit writes for admin CRUD endpoints.

## Notes
- Keep secrets (SMTP/API keys/passwords) in environment variables or a secret manager, not in DB.
- `settings.value_json` is flexible on purpose; use key names like:
  - `scrape.default_frequency_minutes`
  - `scrape.max_total_articles`
  - `email.default_sender`
- Use `normalized_keyword` for case-insensitive duplicate detection.
- `recipients.team_id` can be used as a primary/default team; use `recipient_team_map` for multi-team membership.

## Script usage
1. Install dependency:
   - `.\.venv\Scripts\python.exe -m pip install "psycopg[binary]"`
2. Set DB URL (PowerShell):
   - `$env:DATABASE_URL="postgresql://user:pass@host:5432/dbname"`
3. One-command bootstrap (recommended):
   - Dry run imports: `.\.venv\Scripts\python.exe scripts\db\bootstrap_admin_db.py --dry-run`
   - Full apply: `.\.venv\Scripts\python.exe scripts\db\bootstrap_admin_db.py`
4. Manual mode (optional), run imports in order:
   - `.\.venv\Scripts\python.exe scripts\db\import_keywords.py --dry-run`
   - `.\.venv\Scripts\python.exe scripts\db\import_teams.py --dry-run`
   - `.\.venv\Scripts\python.exe scripts\db\import_recipients.py --dry-run`
5. Re-run without `--dry-run` to commit.

## Bootstrap options
- `--skip-schema`: Skip SQL schema apply step.
- `--skip-keywords`: Skip keyword import.
- `--skip-teams`: Skip team/category import.
- `--skip-recipients`: Skip recipient import.
- `--schema-file <path>`: Use a custom schema SQL path.
- `--team-emails <path>`: Use a custom team emails JSON path.
