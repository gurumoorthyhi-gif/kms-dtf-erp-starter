"""Placeholder pages for the Phase 3 application shell."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from app.ui.components.effects import apply_soft_shadow


class PlaceholderPage(QWidget):
    """A presentation-only page used until business modules are implemented."""

    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        card = QFrame()
        card.setObjectName("glassCard")
        card.setMinimumHeight(220)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 28, 30, 28)
        card_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        body_label = QLabel(description)
        body_label.setObjectName("cardBody")
        body_label.setWordWrap(True)

        card_layout.addWidget(title_label)
        card_layout.addWidget(body_label)
        card_layout.addStretch()
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignTop)
        apply_soft_shadow(card)
