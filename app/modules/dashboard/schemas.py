"""Typed dashboard data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class DashboardDateRange:
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class DashboardMetrics:
    todays_orders: int = 0
    pending_orders: int = 0
    in_production: int = 0
    completed_jobs: int = 0
    pending_payments: int = 0
    revenue: Decimal = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class PipelineStage:
    name: str
    count: int = 0


@dataclass(frozen=True, slots=True)
class ActivityItem:
    action: str
    details: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class LowStockItem:
    name: str
    available: Decimal
    reorder_level: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    metrics: DashboardMetrics = field(default_factory=DashboardMetrics)
    pipeline: tuple[PipelineStage, ...] = ()
    recent_activity: tuple[ActivityItem, ...] = ()
    low_stock: tuple[LowStockItem, ...] = ()
