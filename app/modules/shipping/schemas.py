"""Packing and dispatch inputs and summaries."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PackingInput:
    order_id: int
    package_count: int
    package_weight: Decimal
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PackingSummary:
    id: int
    packing_number: str
    order_id: int
    order_number: str
    customer_name: str
    packing_list: str
    package_count: int
    package_weight: Decimal
    is_complete: bool


@dataclass(frozen=True, slots=True)
class DispatchInput:
    packing_id: int
    courier: str
    tracking_number: str
    proof_of_dispatch_path: str = ""
    authorized_override: bool = False


@dataclass(frozen=True, slots=True)
class DispatchSummary:
    id: int
    dispatch_number: str
    order_number: str
    customer_name: str
    courier: str
    tracking_number: str
    dispatch_date: date
    delivery_status: str
    proof_of_dispatch_path: str
    shipping_label_path: str
    events: tuple[tuple[str | None, str, str, datetime], ...]
