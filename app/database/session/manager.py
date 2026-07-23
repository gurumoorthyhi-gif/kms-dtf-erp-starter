"""SQLAlchemy engine and session lifecycle management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

SessionFactory = sessionmaker[Session]


def resolve_database_url(
    database_url: str,
    *,
    base_directory: Path | None = None,
) -> URL:
    """Resolve relative SQLite files without changing other database backends."""

    url = make_url(database_url)
    database = url.database
    if (
        url.get_backend_name() == "sqlite"
        and database is not None
        and database not in {"", ":memory:"}
        and not Path(database).is_absolute()
    ):
        base = (base_directory or Path.cwd()).resolve()
        url = url.set(database=str((base / database).resolve()))
    return url


def create_database_engine(
    database_url: str,
    *,
    echo: bool = False,
    base_directory: Path | None = None,
) -> Engine:
    """Create an engine with backend-appropriate connection options."""

    url = resolve_database_url(database_url, base_directory=base_directory)
    connect_args = {"check_same_thread": False} if url.get_backend_name() == "sqlite" else {}
    engine = create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    if url.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(
    dbapi_connection: DBAPIConnection,
    connection_record: ConnectionPoolEntry,
) -> None:
    del connection_record
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


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
