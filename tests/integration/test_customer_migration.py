from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_customer_migration_creates_customer_tables(tmp_path: Path) -> None:
    url = "sqlite:///customer-migration.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)

    tables = set(inspect(engine).get_table_names())
    customer_columns = {column["name"] for column in inspect(engine).get_columns("customers")}
    address_columns = {
        column["name"] for column in inspect(engine).get_columns("customer_addresses")
    }

    assert {
        "customers",
        "customer_addresses",
        "customer_file_references",
        "customer_storage_dates",
    } <= tables
    assert "delivery_type" in customer_columns
    assert "preferred_courier" in customer_columns
    assert "other_transport_name" in customer_columns
    assert "preferred_rate" in customer_columns
    assert "storage_prefix" in customer_columns
    assert "google_drive_folder_id" in customer_columns
    assert "district" in address_columns
    assert "landmark" in address_columns
    engine.dispose()
