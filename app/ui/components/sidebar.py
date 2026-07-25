"""Expandable navigation sidebar."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.effects import apply_soft_shadow
from app.ui.icons import (
    create_brand_logo,
    create_sidebar_navigation_icon,
    create_sidebar_toggle_icon,
)

COLLAPSED_WIDTH = 82
EXPANDED_WIDTH = 188
ANIMATION_DURATION_MS = 240


class Sidebar(QFrame):
    """Icons-first sidebar controlled by an explicit expand button."""

    navigation_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(COLLAPSED_WIDTH)
        self.setMaximumWidth(COLLAPSED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._expanded = False
        self._collapse_pending = False
        self._compact = False
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
        self._icon_rail = QFrame(self)
        self._icon_rail.setObjectName("iconRail")
        self._build_ui()
        self._icon_rail.lower()
        self._animation = self._build_animation()
        self.set_active_page(self._active_page)
        apply_soft_shadow(self)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def animation_duration(self) -> int:
        return ANIMATION_DURATION_MS

    @property
    def is_compact(self) -> bool:
        return self._compact

    def button_for(self, page_name: str) -> QToolButton:
        """Return a navigation button for tests and shell coordination."""

        return self._buttons[page_name]

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_icon = QLabel()
        brand_icon.setPixmap(create_brand_logo().pixmap(38, 38))
        brand_icon.setFixedSize(38, 38)
        brand_row.addSpacing(8)
        brand_row.addWidget(brand_icon)
        self._brand_name = QLabel("KMS DTF ERP")
        self._brand_name.setObjectName("brandName")
        self._brand_name.setVisible(False)
        brand_row.addWidget(self._brand_name)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        self._toggle_button = QToolButton()
        self._toggle_button.setObjectName("sidebarToggle")
        self._toggle_button.setIcon(create_sidebar_toggle_icon(False, 20))
        self._toggle_button.setIconSize(QSize(20, 20))
        self._toggle_button.setToolTip("Expand navigation")
        self._toggle_button.setAccessibleName("Expand navigation")
        self._toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_button.setFixedSize(38, 38)
        self._toggle_button.clicked.connect(self.toggle)
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.addSpacing(8)
        toggle_row.addWidget(self._toggle_button)
        toggle_row.addStretch()
        scroll = QScrollArea()
        scroll.setObjectName("navigationScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        navigation = QWidget()
        navigation.setObjectName("navigationContent")
        self._navigation_layout = QVBoxLayout(navigation)
        self._navigation_layout.setContentsMargins(0, 0, 0, 0)
        self._navigation_layout.setSpacing(4)

        for page_name, label in self._labels.items():
            button = QToolButton()
            button.setObjectName("navigationButton")
            button.setProperty("active", False)
            button.setProperty("expanded", False)
            button.setIcon(create_sidebar_navigation_icon(page_name))
            button.setIconSize(QSize(38, 38))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setToolTip(label)
            button.setFixedHeight(42)
            button.setFixedWidth(46)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            button.clicked.connect(
                lambda checked=False, name=page_name: self.navigation_requested.emit(name)
            )
            self._buttons[page_name] = button
            self._navigation_layout.addWidget(
                button,
                alignment=Qt.AlignmentFlag.AlignHCenter,
            )

        self._navigation_layout.addSpacerItem(
            QSpacerItem(
                1,
                1,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )
        scroll.setWidget(navigation)
        layout.addWidget(scroll, 1)
        layout.addLayout(toggle_row)

    def _build_animation(self) -> QParallelAnimationGroup:
        group = QParallelAnimationGroup(self)
        for property_name in (b"minimumWidth", b"maximumWidth"):
            animation = QPropertyAnimation(self, property_name, group)
            animation.setDuration(ANIMATION_DURATION_MS)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(animation)
        group.finished.connect(self._finish_animation)
        return group

    def toggle(self) -> None:
        """Expand or collapse navigation from the arrow control."""

        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self) -> None:
        """Animate to the labeled navigation state."""

        if self._expanded and self.width() == EXPANDED_WIDTH:
            return
        self._expanded = True
        self._collapse_pending = False
        self._toggle_button.setIcon(create_sidebar_toggle_icon(True, 20))
        self._toggle_button.setToolTip("Collapse navigation")
        self._toggle_button.setAccessibleName("Collapse navigation")
        self._brand_name.setVisible(False)
        for page_name, button in self._buttons.items():
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            self._navigation_layout.setAlignment(button, Qt.AlignmentFlag.AlignLeft)
            button.setText(self._labels[page_name])
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setToolTip("")
            button.setProperty("expanded", True)
            self._refresh_button_style(button)
        self._animate_width(174 if self._compact else EXPANDED_WIDTH)

    def collapse(self) -> None:
        """Animate to the compact icon-only state."""

        if not self._expanded and self.width() == COLLAPSED_WIDTH:
            return
        self._expanded = False
        self._collapse_pending = True
        self._toggle_button.setIcon(create_sidebar_toggle_icon(False, 20))
        self._toggle_button.setToolTip("Expand navigation")
        self._toggle_button.setAccessibleName("Expand navigation")
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

        if self._collapse_pending and not self._expanded:
            self._collapse_pending = False
            self._brand_name.setVisible(False)
            for page_name, button in self._buttons.items():
                button.setFixedWidth(40 if self._compact else 46)
                self._navigation_layout.setAlignment(
                    button,
                    Qt.AlignmentFlag.AlignHCenter,
                )
                button.setText("")
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                button.setToolTip(self._labels[page_name])
                button.setProperty("expanded", False)
                self._refresh_button_style(button)

    @staticmethod
    def _refresh_button_style(button: QToolButton) -> None:
        button.style().unpolish(button)
        button.style().polish(button)

    def set_active_page(self, page_name: str) -> None:
        """Apply the active-navigation visual state."""

        if page_name not in self._buttons:
            raise KeyError(f"Unknown sidebar page: {page_name}")
        self._active_page = page_name
        for name, button in self._buttons.items():
            button.setProperty("active", name == page_name)
            self._refresh_button_style(button)

    def set_page_visible(self, page_name: str, visible: bool) -> None:
        self._buttons[page_name].setVisible(visible)

    def set_compact_mode(self, compact: bool) -> None:
        """Scale navigation controls for reduced window height and width."""

        if self._compact == compact:
            return
        self._compact = compact
        icon_size = 34 if compact else 38
        button_height = 38 if compact else 42
        font_size = 11 if compact else 13
        self._navigation_layout.setSpacing(3 if compact else 4)
        for button in self._buttons.values():
            button.setIconSize(QSize(icon_size, icon_size))
            button.setFixedHeight(button_height)
            if not self._expanded:
                button.setFixedWidth(40 if compact else 46)
            font = button.font()
            font.setPixelSize(font_size)
            button.setFont(font)
        if self._expanded:
            self._animate_width(174 if compact else EXPANDED_WIDTH)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the reference-style icon rail fixed behind all controls."""

        self._icon_rail.setGeometry(12, 10, 58, max(0, self.height() - 20))
        self._icon_rail.lower()
        super().resizeEvent(event)
