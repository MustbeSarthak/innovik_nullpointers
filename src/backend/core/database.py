"""Database engine, declarative base and session dependency."""

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _engine_kwargs() -> dict:
    """Build engine keyword arguments for the configured database URL."""
    if settings.is_sqlite:
        # SQLite + FastAPI threadpool requires check_same_thread=False.
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(settings.database_url, echo=settings.debug, **_engine_kwargs())

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db() -> None:
    """Create all tables that do not exist yet.

    The schema is intentionally created through SQLAlchemy metadata so the
    project stays dependency-light.  A migration tool can replace this call
    later without touching the models.
    """
    # Importing the models module registers every table on Base.metadata.
    from backend import models  # noqa: F401  (import side effect)

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session scope for non-HTTP callers.

    Used by the MCP tools, which run outside of a FastAPI request and therefore
    cannot depend on :func:`get_db`.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
