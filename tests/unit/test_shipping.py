from decimal import Decimal
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.database import Base, create_database_engine, create_session_factory
from app.modules.customers import CustomerInput, CustomerRepository, CustomerService
from app.modules.orders import OrderInput, OrderItemInput, OrderRepository, OrderService
from app.modules.products import ProductInput, ProductRepository, ProductService
from app.modules.shipping import (
    DispatchInput,
    DispatchService,
    PackingInput,
    PackingService,
    ShippingRepository,
)


@pytest.fixture
def shipping(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'shipping.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    customers = CustomerService(CustomerRepository(factory))
    products = ProductService(ProductRepository(factory))
    customer = customers.create_customer(CustomerInput("CUS-1", "Customer", "9876543210"))
    category_id, _ = products.create_category("DTF")
    product = products.create_product(
        ProductInput(
            "DTF-1",
            "DTF Print",
            category_id,
            "metre",
            Decimal("100"),
            Decimal("0"),
        )
    )
    orders = OrderService(OrderRepository(factory), products)
    order = orders.create_order(
        OrderInput(customer.summary.id, (OrderItemInput(product.id, Decimal("3")),))
    )
    repository = ShippingRepository(factory)
    yield (
        PackingService(repository),
        DispatchService(repository),
        repository,
        order.summary.id,
        tmp_path,
    )
    engine.dispose()


def test_create_and_complete_packing_with_order_snapshot(shipping) -> None:
    packing, _, _, order_id, _ = shipping

    created = packing.create(PackingInput(order_id, 2, Decimal("4.250"), "Fragile"))
    completed = packing.complete(created.id)

    assert created.packing_number.startswith("PKG-")
    assert "DTF-1 - DTF Print" in created.packing_list
    assert created.package_count == 2
    assert completed.is_complete is True


def test_dispatch_before_packing_is_blocked_without_override(shipping) -> None:
    packing, dispatch, _, order_id, _ = shipping
    packed = packing.create(PackingInput(order_id, 1, Decimal("1")))

    with pytest.raises(ValueError, match="must be complete"):
        dispatch.create(DispatchInput(packed.id, "DTDC", "TRACK-1"))

    assert dispatch.list() == []


def test_authorized_override_dispatch_and_notification_are_audited(shipping) -> None:
    packing, dispatch, repository, order_id, _ = shipping
    packed = packing.create(PackingInput(order_id, 1, Decimal("1")))

    sent = dispatch.create(
        DispatchInput(packed.id, "DTDC", "TRACK-OVERRIDE", authorized_override=True)
    )

    assert sent.delivery_status == "Dispatched"
    assert "authorized packing override" in sent.events[0][2]
    assert repository.notification_count(sent.id) == 1


def test_delivery_status_history_and_notifications_are_preserved(shipping) -> None:
    packing, dispatch, repository, order_id, _ = shipping
    packed = packing.complete(packing.create(PackingInput(order_id, 1, Decimal("2.500"))).id)
    sent = dispatch.create(DispatchInput(packed.id, "Blue Dart", "BD-123"))

    transit = dispatch.update_delivery(sent.id, "In Transit", "Reached hub")
    delivered = dispatch.update_delivery(transit.id, "Delivered", "Signed by customer")

    assert [event[1] for event in delivered.events] == [
        "Dispatched",
        "In Transit",
        "Delivered",
    ]
    assert repository.notification_count(sent.id) == 3


def test_shipping_label_and_proof_of_dispatch(shipping, qapp: QApplication) -> None:
    packing, dispatch, _, order_id, tmp_path = shipping
    proof = tmp_path / "proof.jpg"
    proof.write_bytes(b"proof")
    packed = packing.complete(packing.create(PackingInput(order_id, 2, Decimal("3.125"))).id)
    sent = dispatch.create(DispatchInput(packed.id, "Delhivery", "DEL-101", str(proof)))

    label = dispatch.export_shipping_label(sent.id, tmp_path / "labels" / "label.pdf")
    refreshed = dispatch.list()[0]

    assert label.read_bytes().startswith(b"%PDF")
    assert refreshed.shipping_label_path == str(label.resolve())
    assert refreshed.proof_of_dispatch_path == str(proof.resolve())
