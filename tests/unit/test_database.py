from pathlib import Path

import pytest
from sqlalchemy import text

from app.database import (
    Base,
    check_database_health,
    create_database_engine,
    create_session_factory,
    resolve_database_url,
    session_scope,
)


def test_database_health_and_metadata(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'health.db'}")

    assert check_database_health(engine) is True
    assert set(Base.metadata.tables) == {
        "activity_logs",
        "artwork_approvals",
        "artwork_versions",
        "artworks",
        "customer_addresses",
        "customer_file_references",
        "customers",
        "discount_rules",
        "order_items",
        "order_status_history",
        "orders",
        "permissions",
        "price_rules",
        "product_categories",
        "products",
        "role_permissions",
        "roles",
        "tax_configurations",
        "user_roles",
        "users",
    }
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


def test_relative_sqlite_url_resolves_against_application_path(tmp_path: Path) -> None:
    url = resolve_database_url(
        "sqlite:///data/application.db",
        base_directory=tmp_path,
    )

    assert Path(url.database or "") == (tmp_path / "data" / "application.db").resolve()


def test_sqlite_foreign_keys_are_enabled(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'foreign-keys.db'}")

    with engine.connect() as connection:
        enabled = connection.scalar(text("PRAGMA foreign_keys"))

    assert enabled == 1
    engine.dispose()
