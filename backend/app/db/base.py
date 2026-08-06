"""
Declarative base for SQLAlchemy models.

Kept in its own module (separate from models.py and session.py) so that
Alembic's env.py can import Base.metadata without pulling in the async
engine / session machinery.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
