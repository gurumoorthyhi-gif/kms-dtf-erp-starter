"""Application shell top bar."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.effects import apply_soft_shadow


class TopBar(QFrame):
    """Page context and non-interactive foundation status."""

    logout_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(88)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 14, 20, 14)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        self._title = QLabel("Dashboard")
        self._title.setObjectName("pageTitle")
        self._subtitle = QLabel("Workspace overview")
        self._subtitle.setObjectName("pageSubtitle")
        titles.addWidget(self._title)
        titles.addWidget(self._subtitle)

        self._status = QLabel("Foundation mode")
        self._status.setObjectName("statusPill")
        self._logout_button = QPushButton("Log out")
        self._logout_button.setObjectName("secondaryButton")
        self._logout_button.setVisible(False)
        self._logout_button.clicked.connect(self.logout_requested.emit)

        layout.addLayout(titles)
        layout.addStretch()
        layout.addWidget(self._status)
        layout.addWidget(self._logout_button)
        apply_soft_shadow(self)

    @property
    def title(self) -> str:
        return self._title.text()

    def set_page_context(self, title: str, subtitle: str) -> None:
        """Update the visible page context."""

        self._title.setText(title)
        self._subtitle.setText(subtitle)

    def set_authenticated_user(self, full_name: str | None) -> None:
        """Present safe identity context and logout availability."""

        self._status.setText(full_name or "Foundation mode")
        self._logout_button.setVisible(full_name is not None)
