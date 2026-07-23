from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_production_migration_creates_workflow_tables(tmp_path: Path) -> None:
    url = "sqlite:///production.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    assert {"production_jobs", "production_events", "quality_checks"} <= set(
        inspect(engine).get_table_names()
    )
    engine.dispose()
