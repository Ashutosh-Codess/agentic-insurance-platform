"""
Single place for the SQLAlchemy engine, session factory, and declarative
base. Kept deliberately plain — one file, no session-per-module tricks.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Every model inherits from this. Alembic's env.py imports Base.metadata
    from here so autogenerate can see every table."""
    pass


def get_db():
    """FastAPI dependency — yields one session per request, always closed
    afterward. This is the ONLY way a route should get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
