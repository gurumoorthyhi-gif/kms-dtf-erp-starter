"""Inventory, supplier, and purchase workflows."""

from datetime import date
from decimal import Decimal

from app.modules.authentication import AuthenticationService
from app.modules.inventory.repositories import InventoryRepository, PurchaseRepository
from app.modules.inventory.schemas import (
    InventoryItemInput,
    InventorySummary,
    PurchaseInput,
    PurchaseSummary,
    SupplierInput,
    SupplierSummary,
)

INVENTORY_TYPES = (
    "DTF film",
    "Ink",
    "Powder",
    "Packaging",
    "T-shirts",
    "Labels",
    "Stickers",
    "Accessories",
)


class InventoryService:
    def __init__(
        self,
        repository: InventoryRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create_item(self, data: InventoryItemInput) -> InventorySummary:
        self._require("inventory.manage")
        normalized = InventoryItemInput(
            data.sku.strip().upper(),
            data.name.strip(),
            data.item_type.strip(),
            data.unit.strip(),
            data.reorder_level,
            data.unit_cost,
            data.allow_negative,
        )
        if (
            not normalized.sku
            or not normalized.name
            or normalized.item_type not in INVENTORY_TYPES
            or not normalized.unit
            or normalized.reorder_level < 0
            or normalized.unit_cost < 0
        ):
            raise ValueError("Inventory item values are invalid")
        return self._summary(self.repository.create(normalized))

    def list_items(self) -> list[InventorySummary]:
        self._require("inventory.view")
        return [self._summary(item) for item in self.repository.list()]

    def low_stock(self) -> list[InventorySummary]:
        return [item for item in self.list_items() if item.is_low_stock]

    def stock_in(self, item_id: int, quantity: Decimal, notes: str = "") -> InventorySummary:
        if quantity <= 0:
            raise ValueError("Stock-in quantity must be positive")
        return self._move(item_id, quantity, "stock_in", notes)

    def stock_out(self, item_id: int, quantity: Decimal, notes: str = "") -> InventorySummary:
        if quantity <= 0:
            raise ValueError("Stock-out quantity must be positive")
        return self._move(item_id, -quantity, "stock_out", notes)

    def adjust(self, item_id: int, target_quantity: Decimal, reason: str) -> InventorySummary:
        self._require("inventory.manage")
        if not reason.strip():
            raise ValueError("Adjustment reason is required")
        current = self.repository.get(item_id)
        change = target_quantity - current.quantity_on_hand
        if change == 0:
            raise ValueError("Adjustment does not change stock")
        return self._summary(
            self.repository.move(
                item_id,
                change,
                movement_type="adjustment",
                reference="",
                notes=reason.strip(),
                actor_user_id=self._user_id(),
            )
        )

    def _move(
        self, item_id: int, change: Decimal, movement_type: str, notes: str
    ) -> InventorySummary:
        self._require("inventory.manage")
        return self._summary(
            self.repository.move(
                item_id,
                change,
                movement_type=movement_type,
                reference="",
                notes=notes.strip(),
                actor_user_id=self._user_id(),
            )
        )

    def _require(self, permission: str) -> None:
        if self.authentication_service:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if self.authentication_service is None:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None

    @staticmethod
    def _summary(item) -> InventorySummary:
        return InventorySummary(
            item.id,
            item.sku,
            item.name,
            item.item_type,
            item.unit,
            item.quantity_on_hand,
            item.reorder_level,
            item.unit_cost,
            item.quantity_on_hand <= item.reorder_level,
        )


class PurchaseService:
    def __init__(
        self,
        repository: PurchaseRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create_supplier(self, data: SupplierInput) -> SupplierSummary:
        self._require("purchases.manage")
        if not data.code.strip() or not data.name.strip():
            raise ValueError("Supplier code and name are required")
        supplier = self.repository.create_supplier(
            SupplierInput(
                data.code.strip().upper(),
                data.name.strip(),
                data.contact_name.strip(),
                data.phone.strip(),
                data.email.strip().casefold(),
                data.gst_number.strip().upper(),
                data.address.strip(),
                data.notes.strip(),
            )
        )
        return self._supplier(supplier)

    def list_suppliers(self) -> list[SupplierSummary]:
        self._require("purchases.view")
        return [self._supplier(item) for item in self.repository.list_suppliers()]

    def create_purchase(self, data: PurchaseInput) -> PurchaseSummary:
        self._require("purchases.manage")
        if not data.items or any(item.quantity <= 0 or item.unit_cost < 0 for item in data.items):
            raise ValueError("Purchase requires valid line items")
        today = date.today()
        prefix = f"PUR-{today:%Y%m%d}-"
        sequence = self.repository.next_purchase_sequence(prefix)
        return self._purchase(
            self.repository.create_purchase(
                f"{prefix}{sequence:04d}",
                PurchaseInput(
                    data.supplier_id,
                    data.items,
                    data.expected_date,
                    data.notes.strip(),
                ),
            )
        )

    def list_purchases(self) -> list[PurchaseSummary]:
        self._require("purchases.view")
        return [self._purchase(item) for item in self.repository.list_purchases()]

    def receive(self, purchase_id: int) -> PurchaseSummary:
        self._require("purchases.manage")
        return self._purchase(self.repository.receive(purchase_id, self._user_id()))

    def _require(self, permission: str) -> None:
        if self.authentication_service:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if self.authentication_service is None:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None

    @staticmethod
    def _supplier(item) -> SupplierSummary:
        return SupplierSummary(item.id, item.code, item.name, item.phone, item.email)

    @staticmethod
    def _purchase(item) -> PurchaseSummary:
        return PurchaseSummary(
            item.id,
            item.purchase_number,
            item.supplier.name,
            item.status,
            item.order_date,
            item.total,
            len(item.items),
        )
