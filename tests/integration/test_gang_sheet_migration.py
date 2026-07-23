from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_gang_sheet_migration_creates_layout_tables(tmp_path: Path) -> None:
    url = "sqlite:///gang-sheets.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    assert {"gang_sheets", "gang_sheet_items"} <= set(inspect(engine).get_table_names())
    engine.dispose()
