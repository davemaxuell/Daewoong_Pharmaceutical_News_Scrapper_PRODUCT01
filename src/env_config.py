"""Environment loading helpers for server and local runs."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_project_env() -> None:
    """Load env vars from the common project locations.

    Priority:
    1. Existing process environment
    2. PROJECT_ROOT/.env
    3. PROJECT_ROOT/config/.env
    """

    for env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT / "config" / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


def first_env(*names: str, default: str = "") -> str:
    """Return the first non-empty env var among the given names."""

    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return default
