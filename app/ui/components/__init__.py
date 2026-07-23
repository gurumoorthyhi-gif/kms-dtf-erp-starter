"""Reusable application-shell components."""

from app.ui.components.dashboard import (
    DashboardFilterBar,
    KpiCard,
    LowStockWidget,
    ProductionPipelineWidget,
    QuickActionsWidget,
    RecentActivityWidget,
    apply_metrics,
)
from app.ui.components.sidebar import (
    ANIMATION_DURATION_MS,
    COLLAPSED_WIDTH,
    EXPANDED_WIDTH,
    Sidebar,
)
from app.ui.components.top_bar import TopBar

__all__ = [
    "ANIMATION_DURATION_MS",
    "COLLAPSED_WIDTH",
    "DashboardFilterBar",
    "EXPANDED_WIDTH",
    "KpiCard",
    "LowStockWidget",
    "ProductionPipelineWidget",
    "QuickActionsWidget",
    "RecentActivityWidget",
    "Sidebar",
    "TopBar",
    "apply_metrics",
]
