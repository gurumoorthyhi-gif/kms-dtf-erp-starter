from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_inventory_migration_creates_purchasing_tables(tmp_path: Path) -> None:
    url = "sqlite:///inventory.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    assert {
        "inventory_items",
        "inventory_movements",
        "suppliers",
        "purchases",
        "purchase_items",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()
