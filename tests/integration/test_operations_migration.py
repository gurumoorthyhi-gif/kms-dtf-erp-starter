from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_operations_migration_creates_backup_and_audit_tables(tmp_path: Path) -> None:
    url = "sqlite:///operations.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)
    assert {"backup_history", "audit_records"} <= set(inspect(engine).get_table_names())
    engine.dispose()
