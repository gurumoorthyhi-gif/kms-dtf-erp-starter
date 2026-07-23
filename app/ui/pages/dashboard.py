"""Service-backed operational dashboard."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.modules.dashboard import (
    DashboardPeriod,
    DashboardService,
    EmptyDashboardRepository,
)
from app.ui.components import (
    DashboardFilterBar,
    KpiCard,
    LowStockWidget,
    ProductionPipelineWidget,
    QuickActionsWidget,
    RecentActivityWidget,
    apply_metrics,
)


class DashboardPage(QWidget):
    """Operational overview without direct database access."""

    navigation_requested = Signal(str)

    def __init__(
        self,
        dashboard_service: DashboardService | None = None,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = dashboard_service or DashboardService(EmptyDashboardRepository())
        self._period = DashboardPeriod.TODAY

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_bar = DashboardFilterBar()
        self.error_label = QLabel("")
        self.error_label.setObjectName("dashboardError")
        self.error_label.setVisible(False)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("dashboardContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 12, 16)
        content_layout.setSpacing(16)

        self.kpi_cards = self._create_kpi_cards()
        kpi_layout = QGridLayout()
        kpi_layout.setSpacing(14)
        for index, card in enumerate(self.kpi_cards.values()):
            kpi_layout.addWidget(card, index // 3, index % 3)

        self.pipeline_widget = ProductionPipelineWidget()
        self.activity_widget = RecentActivityWidget()
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(14)
        middle_layout.addWidget(self.pipeline_widget, 3)
        middle_layout.addWidget(self.activity_widget, 2)

        self.low_stock_widget = LowStockWidget()
        self.quick_actions_widget = QuickActionsWidget()
        lower_layout = QHBoxLayout()
        lower_layout.setSpacing(14)
        lower_layout.addWidget(self.low_stock_widget, 3)
        lower_layout.addWidget(self.quick_actions_widget, 2)

        content_layout.addLayout(kpi_layout)
        content_layout.addLayout(middle_layout)
        content_layout.addLayout(lower_layout)
        content_layout.addStretch()
        scroll.setWidget(content)

        root_layout.addWidget(self.filter_bar)
        root_layout.addWidget(self.error_label)
        root_layout.addWidget(scroll, 1)

        self.filter_bar.period_changed.connect(self._change_period)
        self.quick_actions_widget.action_requested.connect(self._handle_action)
        if auto_refresh:
            self.refresh()

    @staticmethod
    def _create_kpi_cards() -> dict[str, KpiCard]:
        return {
            "todays_orders": KpiCard("Today's orders", accent="purple"),
            "pending_orders": KpiCard("Pending orders", accent="blue"),
            "in_production": KpiCard("In production", accent="cyan"),
            "completed_jobs": KpiCard("Completed jobs", accent="green"),
            "pending_payments": KpiCard("Pending payments", accent="pink"),
            "revenue": KpiCard("Revenue", accent="purple"),
        }

    def refresh(self) -> None:
        """Request a fresh typed snapshot from the dashboard service."""

        self.error_label.setVisible(False)
        try:
            overview = self._service.get_overview(self._period)
        except Exception:
            self.error_label.setText("Dashboard data is temporarily unavailable")
            self.error_label.setVisible(True)
            return

        apply_metrics(self.kpi_cards, overview.metrics)
        self.pipeline_widget.set_stages(overview.pipeline)
        self.activity_widget.set_items(overview.recent_activity)
        self.low_stock_widget.set_items(overview.low_stock)

    def _change_period(self, period: str) -> None:
        self._period = DashboardPeriod(period)
        self.refresh()

    def _handle_action(self, action: str) -> None:
        if action == "refresh":
            self.refresh()
        else:
            self.navigation_requested.emit(action)
