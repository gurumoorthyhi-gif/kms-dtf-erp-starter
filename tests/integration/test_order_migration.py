from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_order_migration_creates_order_tables(tmp_path: Path) -> None:
    url = "sqlite:///orders.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    assert {"orders", "order_items", "order_status_history"} <= set(
        inspect(engine).get_table_names()
    )
    assert any(
        index["unique"] and index["column_names"] == ["order_number"]
        for index in inspect(engine).get_indexes("orders")
    )
    engine.dispose()
