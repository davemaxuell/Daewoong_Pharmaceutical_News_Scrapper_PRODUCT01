"""Create an admin user for the admin API."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.admin_api.auth import hash_password  # noqa: E402
from src.admin_api.models import Role, User, UserRole  # noqa: E402


def to_sqlalchemy_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--username", default=None, help="Admin username for login")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--full-name", default=None, help="Admin display name")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    email = args.email.lower().strip()
    engine = create_engine(to_sqlalchemy_url(args.db_url), pool_pre_ping=True)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with session_local() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                username=(args.username.lower().strip() if args.username else None),
                password_hash=hash_password(args.password),
                full_name=args.full_name,
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.password_hash = hash_password(args.password)
            user.full_name = args.full_name or user.full_name
            if args.username:
                user.username = args.username.lower().strip()
            user.is_active = True

        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            raise RuntimeError("Role 'admin' not found. Run DB schema bootstrap first.")

        exists = (
            db.query(UserRole)
            .filter(UserRole.user_id == user.id, UserRole.role_id == admin_role.id)
            .first()
        )
        if not exists:
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))

        db.commit()

    print(f"Admin user ready: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
