from decimal import Decimal
from pathlib import Path

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.modules.products import ProductInput, ProductRepository, ProductService


@pytest.fixture
def pricing(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path/'pricing.db'}")
    Base.metadata.create_all(engine)
    repository = ProductRepository(create_session_factory(engine))
    service = ProductService(repository)
    category_id, _ = service.create_category("DTF Printing")
    product = service.create_product(
        ProductInput("DTF-M", "DTF per metre", category_id, "metre", Decimal("100"), Decimal("18"))
    )
    service.add_price_rule(product.id, Decimal("10"), Decimal("90"))
    service.add_price_rule(product.id, Decimal("20"), Decimal("80"))
    yield service, product.id
    engine.dispose()


@pytest.mark.parametrize(
    ("quantity", "unit_price"), [("9", "100.00"), ("10", "90.00"), ("19", "90.00"), ("20", "80.00")]
)
def test_configurable_tier_boundaries(pricing, quantity: str, unit_price: str) -> None:
    service, product_id = pricing
    result = service.calculate_price(product_id, Decimal(quantity))
    assert result.unit_price == Decimal(unit_price)


def test_discount_and_tax_are_decimal_safe(pricing) -> None:
    service, product_id = pricing
    service.add_discount_rule("Bulk", Decimal("1000"), Decimal("10"))
    result = service.calculate_price(product_id, Decimal("20"))
    assert result.subtotal == Decimal("1600.00")
    assert result.discount == Decimal("160.00")
    assert result.tax == Decimal("259.20")
    assert result.total == Decimal("1699.20")


def test_existing_tier_can_be_changed(pricing) -> None:
    service, product_id = pricing
    service.add_price_rule(product_id, Decimal("10"), Decimal("85"))

    result = service.calculate_price(product_id, Decimal("10"))

    assert result.unit_price == Decimal("85.00")
