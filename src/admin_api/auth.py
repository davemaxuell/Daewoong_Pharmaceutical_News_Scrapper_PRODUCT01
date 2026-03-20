"""Authentication and authorization helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .models import Role, User, UserRole


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def create_access_token(user_id: UUID) -> str:
    from .config import settings

    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> UUID | None:
    from .config import settings

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None


def get_user_roles(db: Session, user_id: UUID) -> list[str]:
    rows = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [name for (name,) in rows]


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    login_value = username.lower().strip()
    user = (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            User.username == login_value,
        )
        .first()
    )
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
