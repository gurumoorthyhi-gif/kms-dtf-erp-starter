"""Operational dashboard use cases."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from enum import StrEnum

from app.modules.authentication import AuthenticationService
from app.modules.dashboard.repository import DashboardDataSource
from app.modules.dashboard.schemas import DashboardDateRange, DashboardOverview


class DashboardPeriod(StrEnum):
    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"


class DashboardService:
    """Combine read-only dashboard data for one selected period."""

    def __init__(
        self,
        repository: DashboardDataSource,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self._repository = repository
        self._authentication_service = authentication_service

    def get_overview(
        self,
        period: DashboardPeriod = DashboardPeriod.TODAY,
        *,
        now: datetime | None = None,
    ) -> DashboardOverview:
        if self._authentication_service is not None:
            self._authentication_service.require_permission("dashboard.view")

        date_range = self._build_date_range(period, now=now)
        return DashboardOverview(
            metrics=self._repository.get_metrics(date_range),
            pipeline=self._repository.get_pipeline(date_range),
            recent_activity=self._repository.get_recent_activity(date_range, limit=8),
            low_stock=self._repository.get_low_stock(),
        )

    @staticmethod
    def _build_date_range(
        period: DashboardPeriod,
        *,
        now: datetime | None,
    ) -> DashboardDateRange:
        current = now or datetime.now(UTC)
        current = current if current.tzinfo is not None else current.replace(tzinfo=UTC)
        days = {
            DashboardPeriod.TODAY: 0,
            DashboardPeriod.LAST_7_DAYS: 6,
            DashboardPeriod.LAST_30_DAYS: 29,
        }[period]
        start_date = current.date() - timedelta(days=days)
        start = datetime.combine(start_date, time.min, tzinfo=current.tzinfo)
        return DashboardDateRange(start=start, end=current)
