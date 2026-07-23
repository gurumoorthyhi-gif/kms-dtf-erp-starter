from pathlib import Path

from sqlalchemy import inspect

from app.database import create_database_engine, upgrade_database


def test_product_migration(tmp_path: Path) -> None:
    url = "sqlite:///products.db"
    upgrade_database(url, base_directory=tmp_path)
    engine = create_database_engine(url, base_directory=tmp_path)
    assert {
        "products",
        "product_categories",
        "price_rules",
        "discount_rules",
        "tax_configurations",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()
