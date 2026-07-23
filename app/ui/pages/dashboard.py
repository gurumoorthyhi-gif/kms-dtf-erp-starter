"""Dashboard placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.pages.placeholder import PlaceholderPage


class DashboardPage(PlaceholderPage):
    """Phase 3 dashboard placeholder without metrics or business behavior."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Dashboard foundation",
            "Dashboard widgets and operational metrics will be introduced in a later phase.",
            parent,
        )
