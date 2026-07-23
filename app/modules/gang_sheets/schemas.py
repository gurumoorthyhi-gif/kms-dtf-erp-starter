"""Gang sheet inputs and layout records."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class GangSheetInput:
    name: str
    width_mm: Decimal
    length_mm: Decimal
    margin_mm: Decimal = Decimal("5")
    spacing_mm: Decimal = Decimal("3")
    order_id: int | None = None


@dataclass(frozen=True, slots=True)
class Placement:
    id: int
    artwork_version_id: int
    artwork_title: str
    preview_path: str
    x_mm: Decimal
    y_mm: Decimal
    width_mm: Decimal
    height_mm: Decimal
    rotation_degrees: int
    z_index: int


@dataclass(frozen=True, slots=True)
class GangSheetDetails:
    id: int
    name: str
    width_mm: Decimal
    length_mm: Decimal
    margin_mm: Decimal
    spacing_mm: Decimal
    metre_usage: Decimal
    items: tuple[Placement, ...]
