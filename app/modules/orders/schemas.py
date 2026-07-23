"""Typed order inputs and presentation records."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderItemInput:
    product_id: int
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class OrderInput:
    customer_id: int
    items: tuple[OrderItemInput, ...]
    advance: Decimal = Decimal("0")
    due_date: date | None = None
    priority: str = "Normal"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PricedOrderItem:
    product_id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class OrderItemDetails:
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class StatusHistoryItem:
    from_status: str | None
    to_status: str
    note: str
    changed_at: datetime


@dataclass(frozen=True, slots=True)
class OrderSummary:
    id: int
    order_number: str
    customer_name: str
    status: str
    priority: str
    due_date: date | None
    total: Decimal
    balance: Decimal


@dataclass(frozen=True, slots=True)
class OrderDetails:
    summary: OrderSummary
    notes: str
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    advance: Decimal
    items: tuple[OrderItemDetails, ...]
    status_history: tuple[StatusHistoryItem, ...]
