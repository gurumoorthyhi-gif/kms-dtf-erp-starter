"""Read-only dashboard persistence queries."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select

from app.database import SessionFactory, session_scope
from app.modules.authentication.models import ActivityLog
from app.modules.dashboard.schemas import (
    ActivityItem,
    DashboardDateRange,
    DashboardMetrics,
    LowStockItem,
    PipelineStage,
)

PIPELINE_STAGES = (
    "Design",
    "Approval",
    "Gang Sheet",
    "Production",
    "Quality Check",
    "Packing",
    "Dispatch",
)


class DashboardDataSource(Protocol):
    """Repository contract consumed by the dashboard service."""

    def get_metrics(self, date_range: DashboardDateRange) -> DashboardMetrics: ...

    def get_pipeline(self, date_range: DashboardDateRange) -> tuple[PipelineStage, ...]: ...

    def get_recent_activity(
        self,
        date_range: DashboardDateRange,
        *,
        limit: int,
    ) -> tuple[ActivityItem, ...]: ...

    def get_low_stock(self) -> tuple[LowStockItem, ...]: ...


class DashboardRepository:
    """Read dashboard data without introducing future-phase business tables."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def get_metrics(self, date_range: DashboardDateRange) -> DashboardMetrics:
        del date_range
        return DashboardMetrics()

    def get_pipeline(self, date_range: DashboardDateRange) -> tuple[PipelineStage, ...]:
        del date_range
        return tuple(PipelineStage(stage) for stage in PIPELINE_STAGES)

    def get_recent_activity(
        self,
        date_range: DashboardDateRange,
        *,
        limit: int,
    ) -> tuple[ActivityItem, ...]:
        with session_scope(self._session_factory) as session:
            statement = (
                select(ActivityLog)
                .where(
                    ActivityLog.created_at >= date_range.start,
                    ActivityLog.created_at <= date_range.end,
                )
                .order_by(ActivityLog.created_at.desc())
                .limit(limit)
            )
            activities = session.scalars(statement)
            return tuple(
                ActivityItem(
                    action=activity.action,
                    details=activity.details,
                    occurred_at=activity.created_at,
                )
                for activity in activities
            )

    def get_low_stock(self) -> tuple[LowStockItem, ...]:
        return ()


class EmptyDashboardRepository:
    """Safe presentation source used before persistence is injected."""

    def get_metrics(self, date_range: DashboardDateRange) -> DashboardMetrics:
        del date_range
        return DashboardMetrics()

    def get_pipeline(self, date_range: DashboardDateRange) -> tuple[PipelineStage, ...]:
        del date_range
        return tuple(PipelineStage(stage) for stage in PIPELINE_STAGES)

    def get_recent_activity(
        self,
        date_range: DashboardDateRange,
        *,
        limit: int,
    ) -> tuple[ActivityItem, ...]:
        del date_range, limit
        return ()

    def get_low_stock(self) -> tuple[LowStockItem, ...]:
        return ()
