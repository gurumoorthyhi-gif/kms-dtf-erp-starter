"""SQLAlchemy engine and session lifecycle management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

SessionFactory = sessionmaker[Session]


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine with backend-appropriate connection options."""

    url = make_url(database_url)
    connect_args = {"check_same_thread": False} if url.get_backend_name() == "sqlite" else {}
    return create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> SessionFactory:
    """Create the application's configured session factory."""

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(session_factory: SessionFactory) -> Iterator[Session]:
    """Provide a transaction that commits on success and rolls back on failure."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
