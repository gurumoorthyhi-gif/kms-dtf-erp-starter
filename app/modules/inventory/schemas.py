"""Inventory and purchase inputs and summaries."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class InventoryItemInput:
    sku: str
    name: str
    item_type: str
    unit: str
    reorder_level: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    allow_negative: bool = False


@dataclass(frozen=True, slots=True)
class InventorySummary:
    id: int
    sku: str
    name: str
    item_type: str
    unit: str
    quantity_on_hand: Decimal
    reorder_level: Decimal
    unit_cost: Decimal
    is_low_stock: bool


@dataclass(frozen=True, slots=True)
class SupplierInput:
    code: str
    name: str
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    gst_number: str = ""
    address: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SupplierSummary:
    id: int
    code: str
    name: str
    phone: str
    email: str


@dataclass(frozen=True, slots=True)
class PurchaseItemInput:
    inventory_item_id: int
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseInput:
    supplier_id: int
    items: tuple[PurchaseItemInput, ...]
    expected_date: date | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PurchaseSummary:
    id: int
    purchase_number: str
    supplier_name: str
    status: str
    order_date: date
    total: Decimal
    item_count: int
