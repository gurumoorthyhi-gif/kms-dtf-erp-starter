from pathlib import Path

import pytest
from sqlalchemy import text

from app.database import (
    Base,
    check_database_health,
    create_database_engine,
    create_session_factory,
    session_scope,
)


def test_database_health_and_metadata(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'health.db'}")

    assert check_database_health(engine) is True
    assert Base.metadata.tables == {}

    engine.dispose()


def test_session_scope_commits_and_rolls_back(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'sessions.db'}")
    factory = create_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE probe (value INTEGER NOT NULL)"))

    with session_scope(factory) as session:
        session.execute(text("INSERT INTO probe (value) VALUES (1)"))

    with pytest.raises(RuntimeError):
        with session_scope(factory) as session:
            session.execute(text("INSERT INTO probe (value) VALUES (2)"))
            raise RuntimeError("force rollback")

    with engine.connect() as connection:
        count = connection.scalar(text("SELECT COUNT(*) FROM probe"))

    assert count == 1
    engine.dispose()


def test_database_health_reports_unavailable_sqlite_path(tmp_path: Path) -> None:
    missing_parent = tmp_path / "missing" / "database.db"
    engine = create_database_engine(f"sqlite:///{missing_parent}")

    assert check_database_health(engine) is False

    engine.dispose()
