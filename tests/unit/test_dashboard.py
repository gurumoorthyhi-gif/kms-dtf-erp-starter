from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from app.database import (
    Base,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.modules.authentication.models import ActivityLog
from app.modules.dashboard import (
    DashboardMetrics,
    DashboardOverview,
    DashboardPeriod,
    DashboardRepository,
    DashboardService,
    EmptyDashboardRepository,
)


class RecordingDashboardRepository(EmptyDashboardRepository):
    def __init__(self) -> None:
        self.date_ranges = []

    def get_metrics(self, date_range):
        self.date_ranges.append(date_range)
        return DashboardMetrics(revenue=Decimal("125.50"))


def test_dashboard_service_builds_selected_date_range() -> None:
    repository = RecordingDashboardRepository()
    service = DashboardService(repository)
    now = datetime(2026, 7, 23, 15, 30, tzinfo=UTC)

    overview = service.get_overview(DashboardPeriod.LAST_7_DAYS, now=now)

    assert overview.metrics.revenue == Decimal("125.50")
    assert repository.date_ranges[0].start == datetime(2026, 7, 17, tzinfo=UTC)
    assert repository.date_ranges[0].end == now


def test_empty_dashboard_is_safe_and_complete() -> None:
    overview = DashboardService(EmptyDashboardRepository()).get_overview()

    assert overview.metrics == DashboardMetrics()
    assert len(overview.pipeline) == 7
    assert all(stage.count == 0 for stage in overview.pipeline)
    assert overview.recent_activity == ()
    assert overview.low_stock == ()


def test_dashboard_repository_reads_existing_activity_only(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'dashboard.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    occurred_at = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)
    with session_scope(factory) as session:
        session.add(
            ActivityLog(
                action="login.succeeded",
                details="Login accepted for admin",
                created_at=occurred_at,
            )
        )

    overview = DashboardService(DashboardRepository(factory)).get_overview(
        now=datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    )

    assert overview.metrics == DashboardMetrics()
    assert len(overview.recent_activity) == 1
    assert overview.recent_activity[0].action == "login.succeeded"
    engine.dispose()


def test_dashboard_overview_defaults_are_independent() -> None:
    first = DashboardOverview()
    second = DashboardOverview()

    assert first.metrics == second.metrics == DashboardMetrics()
