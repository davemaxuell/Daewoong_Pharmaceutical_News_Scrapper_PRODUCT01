"""Runtime helpers for loading admin-managed settings from PostgreSQL."""

from __future__ import annotations

from typing import Any

from src.env_config import first_env, load_project_env


def _as_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_database_url() -> str:
    load_project_env()
    return first_env("DATABASE_URL")


def load_runtime_admin_config() -> dict[str, Any]:
    """Load source/general/schedule settings from the admin DB when available."""

    database_url = _get_database_url()
    if not database_url:
        return {"general": {}, "schedule": None, "sources": {}}

    try:
        from psycopg import connect
    except Exception:
        return {"general": {}, "schedule": None, "sources": {}}

    payload: dict[str, Any] = {
        "general": {},
        "schedule": None,
        "sources": {},
    }

    try:
        with connect(database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key, value_json
                    FROM settings
                    WHERE key = ANY(%s)
                    """,
                    (
                        [
                            "scrape.default_frequency_minutes",
                            "scrape.max_total_articles",
                        ],
                    ),
                )
                for key, value_json in cur.fetchall():
                    value = value_json.get("value") if isinstance(value_json, dict) else None
                    if key == "scrape.default_frequency_minutes":
                        payload["general"]["scrape_frequency_minutes"] = _as_int(value)
                    elif key == "scrape.max_total_articles":
                        payload["general"]["max_total_articles"] = _as_int(value)

                cur.execute(
                    """
                    SELECT name, cron_expr, timezone, is_enabled, last_run_at, next_run_at
                    FROM schedules
                    WHERE name = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    ("default-daily",),
                )
                row = cur.fetchone()
                if row:
                    (
                        name,
                        cron_expr,
                        timezone_name,
                        is_enabled,
                        last_run_at,
                        next_run_at,
                    ) = row
                    payload["schedule"] = {
                        "name": str(name or "default-daily"),
                        "cron_expr": str(cron_expr or "").strip(),
                        "timezone": str(timezone_name or "Asia/Seoul").strip() or "Asia/Seoul",
                        "is_enabled": bool(is_enabled),
                        "last_run_at": last_run_at.isoformat() if last_run_at else None,
                        "next_run_at": next_run_at.isoformat() if next_run_at else None,
                    }

                cur.execute(
                    """
                    SELECT code, display_name, is_enabled, timeout_seconds, max_items
                    FROM sources
                    ORDER BY code ASC
                    """
                )
                for code, display_name, is_enabled, timeout_seconds, max_items in cur.fetchall():
                    source_code = str(code or "").strip()
                    if not source_code:
                        continue
                    payload["sources"][source_code] = {
                        "display_name": str(display_name or source_code).strip() or source_code,
                        "is_enabled": bool(is_enabled),
                        "timeout_seconds": max(1, _as_int(timeout_seconds, 120) or 120),
                        "max_items": max(1, _as_int(max_items, 200) or 200),
                    }
    except Exception as exc:
        print(f"[WARN] Failed to load runtime admin settings from DB: {exc}")
        return {"general": {}, "schedule": None, "sources": {}}

    return payload
