from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_customer_migration_creates_customer_tables(tmp_path: Path) -> None:
    url = "sqlite:///customer-migration.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    tables = set(inspect(engine).get_table_names())

    assert {"customers", "customer_addresses", "customer_file_references"} <= tables
    engine.dispose()
