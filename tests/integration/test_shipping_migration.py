from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_shipping_migration_creates_workflow_tables(tmp_path: Path) -> None:
    url = "sqlite:///shipping.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    assert {
        "packings",
        "dispatches",
        "dispatch_events",
        "customer_notification_events",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()
