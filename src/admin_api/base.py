"""Shared SQLAlchemy base without engine dependencies."""

from sqlalchemy.orm import declarative_base


Base = declarative_base()

