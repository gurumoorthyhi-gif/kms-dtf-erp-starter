"""Settings placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.pages.placeholder import PlaceholderPage


class SettingsPage(PlaceholderPage):
    """Phase 3 settings placeholder without persistence or business behavior."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Settings foundation",
            "Application preferences will be available when the settings module is implemented.",
            parent,
        )
