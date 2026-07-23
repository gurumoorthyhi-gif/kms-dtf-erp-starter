"""Application shell top bar."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.components.effects import apply_soft_shadow


class TopBar(QFrame):
    """Page context and non-interactive foundation status."""

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

        status = QLabel("Foundation mode")
        status.setObjectName("statusPill")

        layout.addLayout(titles)
        layout.addStretch()
        layout.addWidget(status)
        apply_soft_shadow(self)

    @property
    def title(self) -> str:
        return self._title.text()

    def set_page_context(self, title: str, subtitle: str) -> None:
        """Update the visible page context."""

        self._title.setText(title)
        self._subtitle.setText(subtitle)
