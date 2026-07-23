from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_sales_migration_creates_financial_tables(tmp_path: Path) -> None:
    url = "sqlite:///sales.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    assert {"invoices", "invoice_items", "payments", "credit_notes"} <= set(
        inspect(engine).get_table_names()
    )
    engine.dispose()
