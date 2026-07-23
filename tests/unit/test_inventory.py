from decimal import Decimal
from pathlib import Path

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.modules.inventory import (
    InventoryItemInput,
    InventoryRepository,
    InventoryService,
    PurchaseInput,
    PurchaseItemInput,
    PurchaseRepository,
    PurchaseService,
    SupplierInput,
)


@pytest.fixture
def inventory(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'inventory.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    inventory_repository = InventoryRepository(factory)
    purchase_repository = PurchaseRepository(factory)
    yield (
        InventoryService(inventory_repository),
        PurchaseService(purchase_repository),
        inventory_repository,
        purchase_repository,
    )
    engine.dispose()


def make_item(
    service: InventoryService,
    sku: str = "FILM-001",
    *,
    allow_negative: bool = False,
):
    return service.create_item(
        InventoryItemInput(
            sku,
            "DTF Film Roll",
            "DTF film",
            "roll",
            Decimal("5"),
            Decimal("2500"),
            allow_negative,
        )
    )


def test_stock_changes_create_movements_and_low_stock_warning(inventory) -> None:
    service, _, repository, _ = inventory
    item = make_item(service)

    assert service.low_stock()[0].id == item.id
    service.stock_in(item.id, Decimal("10"), "Opening stock")
    service.stock_out(item.id, Decimal("3"), "Production use")
    adjusted = service.adjust(item.id, Decimal("5"), "Physical count")

    movements = repository.movements(item.id)
    assert adjusted.quantity_on_hand == Decimal("5.000")
    assert [movement.movement_type for movement in movements] == [
        "stock_in",
        "stock_out",
        "adjustment",
    ]
    assert [movement.balance_after for movement in movements] == [
        Decimal("10.000"),
        Decimal("7.000"),
        Decimal("5.000"),
    ]


def test_negative_stock_is_rejected_without_recording_movement(inventory) -> None:
    service, _, repository, _ = inventory
    item = make_item(service)

    with pytest.raises(ValueError, match="negative stock"):
        service.stock_out(item.id, Decimal("1"), "Unavailable")

    assert repository.get(item.id).quantity_on_hand == Decimal("0.000")
    assert repository.movements(item.id) == []


def test_negative_stock_can_be_explicitly_allowed(inventory) -> None:
    service, _, repository, _ = inventory
    item = make_item(service, "INK-001", allow_negative=True)

    result = service.stock_out(item.id, Decimal("2"), "Emergency issue")

    assert result.quantity_on_hand == Decimal("-2.000")
    assert repository.movements(item.id)[0].balance_after == Decimal("-2.000")


def test_purchase_receipt_posts_all_stock_movements_atomically(inventory) -> None:
    item_service, purchase_service, item_repository, purchase_repository = inventory
    film = make_item(item_service)
    ink = item_service.create_item(
        InventoryItemInput("INK-001", "Cyan Ink", "Ink", "litre", Decimal("2"), Decimal("800"))
    )
    supplier = purchase_service.create_supplier(
        SupplierInput("SUP-001", "Print Supply Co.", email="BUY@EXAMPLE.COM")
    )
    purchase = purchase_service.create_purchase(
        PurchaseInput(
            supplier.id,
            (
                PurchaseItemInput(film.id, Decimal("2"), Decimal("2400")),
                PurchaseItemInput(ink.id, Decimal("4"), Decimal("750")),
            ),
        )
    )

    received = purchase_service.receive(purchase.id)

    assert received.status == "Received"
    assert received.total == Decimal("7800.00")
    assert item_repository.get(film.id).quantity_on_hand == Decimal("2.000")
    assert item_repository.get(ink.id).quantity_on_hand == Decimal("4.000")
    assert item_repository.movements(film.id)[0].reference == purchase.purchase_number
    assert item_repository.movements(ink.id)[0].movement_type == "purchase_receipt"
    assert purchase_repository.get_purchase(purchase.id).received_date is not None


def test_purchase_cannot_be_received_twice(inventory) -> None:
    item_service, purchase_service, item_repository, _ = inventory
    item = make_item(item_service)
    supplier = purchase_service.create_supplier(SupplierInput("SUP-001", "Supplier"))
    purchase = purchase_service.create_purchase(
        PurchaseInput(
            supplier.id,
            (PurchaseItemInput(item.id, Decimal("2"), Decimal("100")),),
        )
    )
    purchase_service.receive(purchase.id)

    with pytest.raises(ValueError, match="already received"):
        purchase_service.receive(purchase.id)

    assert item_repository.get(item.id).quantity_on_hand == Decimal("2.000")
    assert len(item_repository.movements(item.id)) == 1
