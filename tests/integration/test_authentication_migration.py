from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_authentication_migration_creates_only_phase_four_tables(tmp_path: Path) -> None:
    database_url = "sqlite:///authentication-migration.db"
    upgrade_database(
        database_url,
        base_directory=tmp_path,
        revision="0001_authentication",
    )
    engine = create_database_engine(database_url, base_directory=tmp_path)

    tables = set(inspect(engine).get_table_names())

    assert tables == {
        "activity_logs",
        "alembic_version",
        "permissions",
        "role_permissions",
        "roles",
        "user_roles",
        "users",
    }
    assert (tmp_path / "authentication-migration.db").is_file()
    engine.dispose()
