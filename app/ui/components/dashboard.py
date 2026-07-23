"""Reusable operational dashboard widgets."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.modules.dashboard import (
    ActivityItem,
    DashboardMetrics,
    DashboardPeriod,
    LowStockItem,
    PipelineStage,
)
from app.ui.components.effects import apply_soft_shadow


class KpiCard(QFrame):
    """Single operational metric with consistent glass styling."""

    def __init__(
        self,
        title: str,
        *,
        accent: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setProperty("accent", accent)
        self.setMinimumHeight(118)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("kpiLabel")
        self._value = QLabel("0")
        self._value.setObjectName("kpiValue")
        layout.addWidget(label)
        layout.addWidget(self._value)
        layout.addStretch()
        apply_soft_shadow(self)

    @property
    def value_text(self) -> str:
        return self._value.text()

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class DashboardFilterBar(QFrame):
    """Date-range selection for dashboard refreshes."""

    period_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardFilterBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 12, 8)

        label = QLabel("Overview period")
        label.setObjectName("filterLabel")
        self.period_combo = QComboBox()
        self.period_combo.setObjectName("periodCombo")
        self.period_combo.addItem("Today", DashboardPeriod.TODAY.value)
        self.period_combo.addItem("Last 7 days", DashboardPeriod.LAST_7_DAYS.value)
        self.period_combo.addItem("Last 30 days", DashboardPeriod.LAST_30_DAYS.value)
        self.period_combo.currentIndexChanged.connect(self._emit_period)

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self.period_combo)

    def _emit_period(self) -> None:
        self.period_changed.emit(str(self.period_combo.currentData()))


class ProductionPipelineWidget(QFrame):
    """Compact read-only production-stage overview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardPanel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Production pipeline")
        title.setObjectName("panelTitle")
        self._stage_layout = QGridLayout()
        self._stage_layout.setSpacing(10)
        self._layout.addWidget(title)
        self._layout.addLayout(self._stage_layout)
        self._layout.addStretch()
        apply_soft_shadow(self)

    def set_stages(self, stages: tuple[PipelineStage, ...]) -> None:
        _clear_layout(self._stage_layout)
        for index, stage in enumerate(stages):
            stage_card = QFrame()
            stage_card.setObjectName("pipelineStage")
            stage_layout = QVBoxLayout(stage_card)
            stage_layout.setContentsMargins(12, 10, 12, 10)
            name = QLabel(stage.name)
            name.setObjectName("stageName")
            count = QLabel(str(stage.count))
            count.setObjectName("stageCount")
            stage_layout.addWidget(name)
            stage_layout.addWidget(count)
            self._stage_layout.addWidget(stage_card, index // 4, index % 4)


class RecentActivityWidget(QFrame):
    """Recent auditable system activity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardPanel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Recent activity")
        title.setObjectName("panelTitle")
        self._items = QVBoxLayout()
        self._layout.addWidget(title)
        self._layout.addLayout(self._items)
        self._layout.addStretch()
        apply_soft_shadow(self)

    def set_items(self, items: tuple[ActivityItem, ...]) -> None:
        _clear_layout(self._items)
        if not items:
            empty = QLabel("No activity in this period")
            empty.setObjectName("emptyState")
            self._items.addWidget(empty)
            return
        for item in items:
            row = QFrame()
            row.setObjectName("activityRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 7, 10, 7)
            action = QLabel(item.action.replace(".", " ").title())
            action.setObjectName("activityAction")
            detail = QLabel(item.details)
            detail.setObjectName("activityDetail")
            detail.setWordWrap(True)
            row_layout.addWidget(action)
            row_layout.addWidget(detail)
            self._items.addWidget(row)


class LowStockWidget(QFrame):
    """Low-stock list with a safe pre-inventory empty state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardPanel")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Low stock")
        title.setObjectName("panelTitle")
        self._items = QVBoxLayout()
        self._layout.addWidget(title)
        self._layout.addLayout(self._items)
        self._layout.addStretch()
        apply_soft_shadow(self)
        self.set_items(())

    def set_items(self, items: tuple[LowStockItem, ...]) -> None:
        _clear_layout(self._items)
        if not items:
            empty = QLabel("No low-stock items")
            empty.setObjectName("emptyState")
            self._items.addWidget(empty)
            return
        for item in items:
            text = f"{item.name}: {item.available} {item.unit}"
            label = QLabel(text)
            label.setObjectName("stockItem")
            self._items.addWidget(label)


class QuickActionsWidget(QFrame):
    """Actions limited to functionality already implemented."""

    action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("Quick actions")
        title.setObjectName("panelTitle")
        refresh = QPushButton("Refresh dashboard")
        refresh.setObjectName("dashboardAction")
        settings = QPushButton("Open settings")
        settings.setObjectName("dashboardAction")
        refresh.clicked.connect(lambda: self.action_requested.emit("refresh"))
        settings.clicked.connect(lambda: self.action_requested.emit("settings"))
        layout.addWidget(title)
        layout.addWidget(refresh)
        layout.addWidget(settings)
        layout.addStretch()
        apply_soft_shadow(self)


def apply_metrics(cards: dict[str, KpiCard], metrics: DashboardMetrics) -> None:
    """Format typed service metrics for presentation."""

    cards["todays_orders"].set_value(str(metrics.todays_orders))
    cards["pending_orders"].set_value(str(metrics.pending_orders))
    cards["in_production"].set_value(str(metrics.in_production))
    cards["completed_jobs"].set_value(str(metrics.completed_jobs))
    cards["pending_payments"].set_value(str(metrics.pending_payments))
    cards["revenue"].set_value(f"INR {metrics.revenue:,.2f}")


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif child_layout is not None:
            _clear_layout(child_layout)
