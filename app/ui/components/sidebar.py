"""Expandable navigation sidebar."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Signal,
)
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.effects import apply_soft_shadow
from app.ui.icons import create_gradient_icon

COLLAPSED_WIDTH = 72
EXPANDED_WIDTH = 260
ANIMATION_DURATION_MS = 240


class Sidebar(QFrame):
    """Icons-first sidebar that expands while the pointer is over it."""

    navigation_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(COLLAPSED_WIDTH)
        self.setMaximumWidth(COLLAPSED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._expanded = False
        self._active_page = "dashboard"
        self._buttons: dict[str, QToolButton] = {}
        self._labels = {
            "dashboard": "Dashboard",
            "customers": "Customers",
            "products": "Products",
            "orders": "Orders",
            "artwork": "Artwork",
            "studio": "Artwork Studio",
            "ai_tools": "AI Tools",
            "gang_sheets": "Gang Sheets",
            "production": "Production",
            "inventory": "Inventory",
            "suppliers": "Suppliers",
            "purchases": "Purchases",
            "sales": "Sales",
            "invoices": "Invoices",
            "payments": "Payments",
            "packing": "Packing",
            "dispatch": "Dispatch",
            "cloud_storage": "Cloud Storage",
            "whatsapp": "WhatsApp",
            "email": "Email",
            "operations": "Reports & Backup",
            "settings": "Settings",
        }
        self._build_ui()
        self._animation = self._build_animation()
        self.set_active_page(self._active_page)
        apply_soft_shadow(self)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def animation_duration(self) -> int:
        return ANIMATION_DURATION_MS

    def button_for(self, page_name: str) -> QToolButton:
        """Return a navigation button for tests and shell coordination."""

        return self._buttons[page_name]

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(5, 0, 0, 14)
        brand_icon = QLabel()
        brand_icon.setPixmap(create_gradient_icon("brand", 34).pixmap(34, 34))
        brand_icon.setFixedSize(38, 38)
        self._brand_name = QLabel("KMS DTF ERP")
        self._brand_name.setObjectName("brandName")
        self._brand_name.setVisible(False)
        brand_row.addWidget(brand_icon)
        brand_row.addWidget(self._brand_name)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        for page_name, label in self._labels.items():
            button = QToolButton()
            button.setObjectName("navigationButton")
            button.setProperty("active", False)
            button.setIcon(create_gradient_icon(page_name))
            button.setIconSize(QSize(28, 28))
            button.setToolTip(label)
            button.setFixedHeight(52)
            button.clicked.connect(
                lambda checked=False, name=page_name: self.navigation_requested.emit(name)
            )
            self._buttons[page_name] = button
            layout.addWidget(button)

        layout.addSpacerItem(
            QSpacerItem(
                1,
                1,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )

    def _build_animation(self) -> QParallelAnimationGroup:
        group = QParallelAnimationGroup(self)
        for property_name in (b"minimumWidth", b"maximumWidth"):
            animation = QPropertyAnimation(self, property_name, group)
            animation.setDuration(ANIMATION_DURATION_MS)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(animation)
        group.finished.connect(self._finish_animation)
        return group

    def enterEvent(self, event: QEnterEvent) -> None:
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.collapse()
        super().leaveEvent(event)

    def expand(self) -> None:
        """Animate to the labeled navigation state."""

        if self._expanded and self.width() == EXPANDED_WIDTH:
            return
        self._expanded = True
        self._brand_name.setVisible(True)
        for page_name, button in self._buttons.items():
            button.setText(self._labels[page_name])
            button.setToolTip("")
        self._animate_width(EXPANDED_WIDTH)

    def collapse(self) -> None:
        """Animate to the compact icon-only state."""

        if not self._expanded and self.width() == COLLAPSED_WIDTH:
            return
        self._expanded = False
        self._brand_name.setVisible(False)
        for page_name, button in self._buttons.items():
            button.setText("")
            button.setToolTip(self._labels[page_name])
        self._animate_width(COLLAPSED_WIDTH)

    def _animate_width(self, target_width: int) -> None:
        self._animation.stop()
        for animation in self._animation.children():
            if isinstance(animation, QPropertyAnimation):
                animation.setStartValue(self.width())
                animation.setEndValue(target_width)
        self._animation.start()

    def _finish_animation(self) -> None:
        """Keep a stable signal endpoint for shell animation tests."""

    def set_active_page(self, page_name: str) -> None:
        """Apply the active-navigation visual state."""

        if page_name not in self._buttons:
            raise KeyError(f"Unknown sidebar page: {page_name}")
        self._active_page = page_name
        for name, button in self._buttons.items():
            button.setProperty("active", name == page_name)
            button.style().unpolish(button)
            button.style().polish(button)

    def set_page_visible(self, page_name: str, visible: bool) -> None:
        self._buttons[page_name].setVisible(visible)
