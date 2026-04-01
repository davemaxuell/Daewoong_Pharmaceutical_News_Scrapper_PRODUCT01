"""Admin API settings."""

from __future__ import annotations

import os

from src.env_config import load_project_env


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


class Settings:
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    def __init__(self) -> None:
        load_project_env()
        self.database_url = _get_env("DATABASE_URL")
        self.jwt_secret = _get_env("ADMIN_JWT_SECRET", "change-me")
        self.jwt_algorithm = _get_env("ADMIN_JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            _get_env("ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES", "480")
        )


settings = Settings()
