"""Typed product inputs and outputs."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProductInput:
    code: str
    name: str
    category_id: int
    unit: str
    base_price: Decimal
    tax_rate: Decimal
    size: str = ""
    colour: str = ""
    gsm: str = ""
    style: str = ""


@dataclass(frozen=True, slots=True)
class ProductSummary:
    id: int
    code: str
    name: str
    category: str
    unit: str
    base_price: Decimal
    tax_rate: Decimal
    is_active: bool
