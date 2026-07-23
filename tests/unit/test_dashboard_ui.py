from decimal import Decimal

from app.modules.dashboard import (
    DashboardMetrics,
    DashboardOverview,
    DashboardPeriod,
    PipelineStage,
)
from app.ui.application import MainWindow
from app.ui.pages import DashboardPage


class FakeDashboardService:
    def __init__(self) -> None:
        self.periods: list[DashboardPeriod] = []

    def get_overview(self, period: DashboardPeriod) -> DashboardOverview:
        self.periods.append(period)
        return DashboardOverview(
            metrics=DashboardMetrics(
                todays_orders=3,
                pending_orders=2,
                in_production=1,
                completed_jobs=4,
                pending_payments=5,
                revenue=Decimal("1234.50"),
            ),
            pipeline=(PipelineStage("Production", 1),),
        )


def test_dashboard_page_displays_service_metrics(qtbot) -> None:
    service = FakeDashboardService()
    page = DashboardPage(service)  # type: ignore[arg-type]
    qtbot.addWidget(page)

    assert page.kpi_cards["todays_orders"].value_text == "3"
    assert page.kpi_cards["pending_orders"].value_text == "2"
    assert page.kpi_cards["revenue"].value_text == "INR 1,234.50"
    assert service.periods == [DashboardPeriod.TODAY]


def test_dashboard_date_filter_refreshes_selected_period(qtbot) -> None:
    service = FakeDashboardService()
    page = DashboardPage(service)  # type: ignore[arg-type]
    qtbot.addWidget(page)

    page.filter_bar.period_combo.setCurrentIndex(1)

    assert service.periods[-1] == DashboardPeriod.LAST_7_DAYS


def test_dashboard_quick_action_navigates_to_existing_settings(qtbot) -> None:
    service = FakeDashboardService()
    window = MainWindow(dashboard_service=service)  # type: ignore[arg-type]
    qtbot.addWidget(window)

    window.dashboard_page.navigation_requested.emit("settings")

    assert window.router.current_page_name == "settings"
