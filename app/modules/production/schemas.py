"""Production inputs and presentation records."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProductionJobInput:
    order_id: int
    priority: str = "Normal"
    gang_sheet_id: int | None = None
    due_date: date | None = None
    machine_name: str = ""
    operator_user_id: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ProductionEventDetails:
    event_type: str
    from_stage: str | None
    to_stage: str | None
    details: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QualityCheckInput:
    print_quality_ok: bool
    colour_ok: bool
    curing_ok: bool
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ProductionJobDetails:
    id: int
    order_number: str
    customer_name: str
    stage: str
    priority: str
    machine_name: str
    operator_name: str
    due_date: date | None
    is_paused: bool
    pause_reason: str
    reprint_count: int
    wastage_metres: Decimal
    notes: str
    events: tuple[ProductionEventDetails, ...]
    quality_check_count: int
