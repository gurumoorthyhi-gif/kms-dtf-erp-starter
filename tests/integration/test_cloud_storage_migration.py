from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_cloud_storage_migration_creates_queue_table(tmp_path: Path) -> None:
    url = "sqlite:///cloud.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)
    assert "cloud_files" in inspect(engine).get_table_names()
    engine.dispose()
