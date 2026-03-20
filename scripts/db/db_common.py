"""Shared helpers for PostgreSQL import scripts."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator


def get_database_url(cli_value: str | None) -> str:
    db_url = cli_value or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "Database URL missing. Pass --db-url or set DATABASE_URL environment variable."
        )
    return db_url


def normalize_keyword(value: str) -> str:
    return " ".join(value.strip().lower().split())


@contextmanager
def postgres_connection(db_url: str) -> Iterator[object]:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "psycopg is not installed. Install with: pip install 'psycopg[binary]'"
        ) from exc

    with psycopg.connect(db_url, connect_timeout=5) as conn:
        yield conn
