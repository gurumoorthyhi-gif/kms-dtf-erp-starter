from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.modules.customers import CustomerInput, CustomerRepository, CustomerService
from app.modules.orders import (
    ORDER_STATUSES,
    OrderInput,
    OrderItemInput,
    OrderRepository,
    OrderService,
    generate_order_number,
)
from app.modules.products import ProductInput, ProductRepository, ProductService


@pytest.fixture
def orders(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'orders.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    customers = CustomerService(CustomerRepository(factory))
    products = ProductService(ProductRepository(factory))
    customer = customers.create_customer(CustomerInput("CUS-001", "KMS Customer", "9876543210"))
    category_id, _ = products.create_category("DTF")
    first = products.create_product(
        ProductInput(
            "DTF-M",
            "DTF per metre",
            category_id,
            "metre",
            Decimal("100"),
            Decimal("18"),
        )
    )
    second = products.create_product(
        ProductInput(
            "TSHIRT",
            "T-shirt",
            category_id,
            "piece",
            Decimal("250"),
            Decimal("5"),
        )
    )
    products.add_price_rule(first.id, Decimal("10"), Decimal("90"))
    products.add_discount_rule("Bulk", Decimal("1000"), Decimal("10"))
    service = OrderService(OrderRepository(factory), products)
    yield service, customer.summary.id, first.id, second.id
    engine.dispose()


def test_order_number_format() -> None:
    assert generate_order_number(date(2026, 7, 23), 12) == "KMS-20260723-0012"


def test_create_multi_item_order_calculates_totals_and_balance(orders) -> None:
    service, customer_id, first_id, second_id = orders

    order = service.create_order(
        OrderInput(
            customer_id,
            (
                OrderItemInput(first_id, Decimal("10")),
                OrderItemInput(second_id, Decimal("2")),
            ),
            advance=Decimal("400"),
            due_date=date(2026, 8, 1),
            priority="High",
            notes="Handle carefully",
        )
    )

    assert len(order.items) == 2
    assert order.subtotal == Decimal("1400.00")
    assert order.discount == Decimal("0.00")
    assert order.tax == Decimal("187.00")
    assert order.summary.total == Decimal("1587.00")
    assert order.summary.balance == Decimal("1187.00")
    assert order.status_history[0].to_status == "Draft"
    assert service.get_order(order.summary.id) == order


def test_order_numbers_are_unique_and_status_history_is_kept(orders) -> None:
    service, customer_id, product_id, _ = orders
    data = OrderInput(customer_id, (OrderItemInput(product_id, Decimal("1")),))
    first = service.create_order(data)
    second = service.create_order(data)

    assert first.summary.order_number != second.summary.order_number
    updated = service.change_status(first.summary.id, "Awaiting Artwork", "Need design")
    assert updated.summary.status == "Awaiting Artwork"
    assert [event.to_status for event in updated.status_history] == [
        "Draft",
        "Awaiting Artwork",
    ]
    assert updated.status_history[-1].note == "Need design"


def test_all_required_statuses_are_available() -> None:
    assert len(ORDER_STATUSES) == 16
    assert ORDER_STATUSES[0] == "Draft"
    assert ORDER_STATUSES[-1] == "Cancelled"
