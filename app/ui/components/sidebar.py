"""Animated, custom-painted glass navigation sidebar."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSettings,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.branding import logo_pixmap
from app.ui.icons import create_gradient_icon

COLLAPSED_WIDTH = 78
EXPANDED_WIDTH = COLLAPSED_WIDTH
ANIMATION_DURATION_MS = 200

_MAIN_ITEMS: Sequence[tuple[str, str]] = (
    ("dashboard", "Dashboard"),
    ("customers", "Customers"),
    ("orders", "Orders"),
    ("studio", "Artwork Studio"),
    ("image_editor", "Image Editor"),
    ("inventory", "Inventory"),
    ("purchases", "Purchase"),
    ("sales", "Sales"),
    ("invoices", "Invoices"),
    ("payments", "Payments"),
    ("products", "Products"),
    ("artwork", "Artwork Library"),
    ("suppliers", "Suppliers"),
    ("packing", "Packing"),
    ("dispatch", "Dispatch"),
)

_UTILITY_ITEMS: Sequence[tuple[str, str]] = (
    ("whatsapp", "WhatsApp"),
    ("email", "Mail"),
    ("ai_tools", "AI Tools"),
    ("cloud_storage", "Cloud Storage"),
    ("operations", "Reports & Backup"),
    ("settings", "Settings"),
    ("users", "Users"),
)

_GRADIENTS: dict[str, tuple[str, str]] = {
    "dashboard": ("#895CFF", "#5868FF"),
    "orders": ("#547DFF", "#3264D8"),
    "customers": ("#3E91FF", "#24C4E8"),
    "studio": ("#26BDEB", "#568BFF"),
    "image_editor": ("#7B61FF", "#32C5FF"),
    "inventory": ("#527DFF", "#805FE8"),
    "purchases": ("#8D5EEB", "#D35DAF"),
    "sales": ("#EC5FB4", "#8C5EEB"),
    "invoices": ("#587BE8", "#5961C8"),
    "payments": ("#855FE8", "#6559D5"),
    "whatsapp": ("#35B98B", "#27A8A1"),
    "email": ("#3C8DEA", "#32BBD2"),
    "ai_tools": ("#875CE8", "#5966DE"),
    "cloud_storage": ("#487FE5", "#7761DA"),
    "operations": ("#6389DC", "#A174DA"),
    "settings": ("#64748F", "#7585A7"),
    "users": ("#596DD8", "#8066D8"),
}


class _GlassTooltip(QFrame):
    """Small animated glass label used while the rail is collapsed."""

    entered = Signal()
    left = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self._label = QLabel(self)
        self._label.setStyleSheet(
            "color: rgba(255,255,255,240); font: 600 12px 'Segoe UI'; padding: 0;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 10, 18, 10)
        layout.addWidget(self._label)
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._motion = QPropertyAnimation(self, b"geometry", self)
        self._motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animations = QParallelAnimationGroup(self)
        self._animations.addAnimation(self._fade)
        self._animations.addAnimation(self._motion)
        self._animations.finished.connect(self._animation_finished)
        self._closing = False
        self._dark_mode = True
        self._pending: tuple[QWidget, str] | None = None

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        glow = QRadialGradient(QPoint(20, self.height() // 2), self.width())
        glow.setColorAt(0.0, QColor(102, 118, 255, 72))
        glow.setColorAt(0.45, QColor(86, 110, 225, 30))
        glow.setColorAt(1.0, QColor(62, 78, 180, 0))
        painter.fillRect(self.rect(), glow)
        path = QPainterPath()
        body = QRectF(self.rect()).adjusted(8, 2, -2, -2)
        path.addRoundedRect(body, 13, 13)
        pointer = QPainterPath()
        pointer.moveTo(9, self.height() / 2 - 6)
        pointer.lineTo(1, self.height() / 2)
        pointer.lineTo(9, self.height() / 2 + 6)
        pointer.closeSubpath()
        path.addPath(pointer)
        painter.fillPath(
            path,
            QColor(43, 57, 108, 235) if self._dark_mode else QColor(232, 241, 255, 242),
        )
        painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
        painter.drawPath(path)
        super().paintEvent(event)

    def show_for(self, button: QWidget, text: str) -> None:
        if self.isVisible() and self._label.text() != text and self._opacity.opacity() > 0.08:
            self._pending = (button, text)
            self.fade_out(transfer=True)
            return
        self._open_for(button, text)

    def _open_for(self, button: QWidget, text: str) -> None:
        self._label.setText(text)
        self.adjustSize()
        self.resize(self.width() + 8, max(42, self.height()))
        anchor = button.mapToGlobal(QPoint(button.width() + 11, button.height() // 2))
        final = self.geometry()
        final.moveTopLeft(QPoint(anchor.x(), anchor.y() - final.height() // 2))
        start = final.adjusted(0, 1, 0, -1)
        start.moveLeft(final.left() - 8)
        self._animations.stop()
        self._closing = False
        self._opacity.setOpacity(0.0)
        self.setGeometry(start)
        self.show()
        self.raise_()
        self._fade.setDuration(190)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._motion.setDuration(200)
        self._motion.setStartValue(start)
        self._motion.setEndValue(final)
        self._animations.start()

    def fade_out(self, transfer: bool = False) -> None:
        if not self.isVisible():
            return
        self._animations.stop()
        self._closing = True
        final = self.geometry()
        target = final.adjusted(0, 1, 0, -1)
        target.moveLeft(final.left() - 5)
        self._fade.setDuration(75 if transfer else 140)
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._motion.setDuration(75 if transfer else 130)
        self._motion.setStartValue(final)
        self._motion.setEndValue(target)
        self._animations.start()

    def _animation_finished(self) -> None:
        if self._closing:
            self.hide()
            if self._pending is not None:
                button, text = self._pending
                self._pending = None
                self._open_for(button, text)

    def set_dark_mode(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        text_color = "#F6F9FF" if dark_mode else "#20345E"
        self._label.setStyleSheet(f"color: {text_color}; font: 600 12px 'Segoe UI'; padding: 0;")
        self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        self.entered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.left.emit()
        super().leaveEvent(event)


class GlassNavigationButton(QToolButton):
    """Navigation row painted as a layered glass control."""

    hovered = Signal(object, bool)

    def __init__(self, page_name: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page_name = page_name
        self.label = label
        self._hover_progress = 0.0
        self._reveal_progress = 0.0
        self._active = False
        self._dark_mode = True
        self.setObjectName("glassNavigationButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setIcon(create_gradient_icon(page_name, 24, dark_mode=True))
        self.setIconSize(QSize(22, 22))
        self.setToolTip(label)
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(190)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._reveal_animation = QPropertyAnimation(self, b"revealProgress", self)
        self._reveal_animation.setDuration(230)
        self._reveal_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(24)
        glow.setOffset(0, 3)
        glow.setColor(QColor(69, 111, 255, 105))
        self.setGraphicsEffect(glow)

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, value: float) -> None:
        self._hover_progress = value
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setBlurRadius(24 + (26 * value) + (20 if self._active else 0))
            effect.setColor(
                QColor(91, 105, 255, int(105 + (105 * value) + (35 if self._active else 0)))
            )
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def get_reveal_progress(self) -> float:
        return self._reveal_progress

    def set_reveal_progress(self, value: float) -> None:
        self._reveal_progress = value
        self.update()

    revealProgress = Property(float, get_reveal_progress, set_reveal_progress)

    def set_revealed(self, revealed: bool, animated: bool = True) -> None:
        target = 1.0 if revealed else 0.0
        self.setText(self.label if revealed else "")
        self.setToolTip("" if revealed else self.label)
        self._reveal_animation.stop()
        if not animated:
            self.set_reveal_progress(target)
            return
        self._reveal_animation.setStartValue(self._reveal_progress)
        self._reveal_animation.setEndValue(target)
        self._reveal_animation.start()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", active)
        self.set_hover_progress(self._hover_progress)

    def set_dark_mode(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self.setIcon(create_gradient_icon(self.page_name, 24, dark_mode=dark_mode))
        self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate_hover(1.0)
        self.hovered.emit(self, True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_hover(0.0)
        self.hovered.emit(self, False)
        super().leaveEvent(event)

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = 1.0 + (0.10 * self._hover_progress)
        icon_size = 46 * scale
        icon_rect = QRectF(
            (self.width() - icon_size) / 2,
            (self.height() - icon_size) / 2 - self._hover_progress,
            icon_size,
            icon_size,
        )
        if self._active or self._hover_progress:
            outer_glow = QRadialGradient(icon_rect.center(), 36)
            active_alpha = 145 if self._active else 0
            hover_alpha = int(175 * self._hover_progress)
            outer_glow.setColorAt(0, QColor(132, 84, 255, min(235, active_alpha + hover_alpha)))
            outer_glow.setColorAt(
                0.45,
                QColor(
                    57 if self._dark_mode else 70,
                    140 if self._dark_mode else 88,
                    255,
                    min(190, (100 if self._active else 0) + int(120 * self._hover_progress)),
                ),
            )
            outer_glow.setColorAt(
                0.72,
                QColor(
                    38,
                    222,
                    255,
                    min(125, (38 if self._active else 0) + int(90 * self._hover_progress)),
                ),
            )
            outer_glow.setColorAt(1, QColor(80, 120, 255, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(outer_glow)
            painter.drawEllipse(icon_rect.adjusted(-12, -12, 12, 12))

        icon_pixels = round(22 * scale)
        icon = self.icon().pixmap(icon_pixels, icon_pixels)
        normal_opacity = 0.66 if self._dark_mode else 0.72
        painter.setOpacity(1.0 if (self._active or self._hover_progress > 0.01) else normal_opacity)
        painter.drawPixmap(
            int(icon_rect.center().x() - icon_pixels / 2),
            int(icon_rect.center().y() - icon_pixels / 2),
            icon,
        )

        if self._reveal_progress > 0.01:
            painter.setOpacity(self._reveal_progress)
            font = QFont("Segoe UI", 10)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor(245, 248, 255, 242))
            text_rect = QRectF(59 - (10 * (1 - self._reveal_progress)), 0, self.width() - 68, 50)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.label)
        painter.end()


class ThemeToggleButton(QToolButton):
    """Transparent animated sun/moon theme control."""

    theme_toggled = Signal(bool)

    def __init__(self, dark_mode: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._progress = 0.0 if dark_mode else 1.0
        self._dark_mode = dark_mode
        self.setObjectName("themeToggleButton")
        self.setFixedSize(46, 46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle)
        self._animation = QPropertyAnimation(self, b"themeProgress", self)
        self._animation.setDuration(350)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._update_tooltip()

    def get_theme_progress(self) -> float:
        return self._progress

    def set_theme_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    themeProgress = Property(float, get_theme_progress, set_theme_progress)

    def _toggle(self) -> None:
        self._dark_mode = not self._dark_mode
        self._animation.stop()
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(0.0 if self._dark_mode else 1.0)
        self._animation.start()
        self._update_tooltip()
        self.theme_toggled.emit(self._dark_mode)

    def _update_tooltip(self) -> None:
        self.setToolTip("Switch to Light Mode" if self._dark_mode else "Switch to Dark Mode")

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPoint(self.width() // 2, self.height() // 2)

        painter.save()
        painter.translate(center)
        painter.rotate(100 * self._progress)
        painter.scale(1.0 - (0.18 * self._progress), 1.0 - (0.18 * self._progress))
        painter.setOpacity(1.0 - self._progress)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#DDEBFF"))
        painter.drawEllipse(QPoint(0, 0), 9, 9)
        painter.setBrush(QColor(45, 58, 111))
        painter.drawEllipse(QPoint(4, -3), 8, 8)
        painter.restore()

        painter.save()
        painter.translate(center)
        painter.rotate(-90 * (1.0 - self._progress))
        sun_scale = 0.82 + (0.18 * self._progress)
        painter.scale(sun_scale, sun_scale)
        painter.setOpacity(self._progress)
        pen = QPen(QColor("#354D86"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QColor("#D3A73D"))
        painter.drawEllipse(QPoint(0, 0), 7, 7)
        for angle in range(0, 360, 45):
            painter.save()
            painter.rotate(angle)
            painter.drawLine(QPoint(0, -11), QPoint(0, -15))
            painter.restore()
        painter.restore()


class Sidebar(QFrame):
    """A permanently collapsed glass rail with one reusable hover flyout."""

    navigation_requested = Signal(str)
    theme_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(COLLAPSED_WIDTH)
        self.setMaximumWidth(COLLAPSED_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._expanded = False
        self._active_page = "dashboard"
        self._buttons: dict[str, GlassNavigationButton] = {}
        self._labels = dict((*_MAIN_ITEMS, *_UTILITY_ITEMS))
        self._settings = QSettings("KMS", "DTF ERP")
        self._dark_mode = self._settings.value("ui/theme", "dark") != "light"
        self._tooltip = _GlassTooltip()
        self.destroyed.connect(self._tooltip.close)
        self._current_button: GlassNavigationButton | None = None
        self._tooltip.entered.connect(self._tooltip_entered)
        self._tooltip.left.connect(self._tooltip_left)
        self._tooltip_hide_timer = QTimer(self)
        self._tooltip_hide_timer.setSingleShot(True)
        self._tooltip_hide_timer.setInterval(85)
        self._tooltip_hide_timer.timeout.connect(self._tooltip.fade_out)
        self._build_ui()
        self.setFixedWidth(COLLAPSED_WIDTH)
        self.set_dark_mode(self._dark_mode)
        self.set_active_page(self._active_page)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def is_pinned(self) -> bool:
        return False

    @property
    def animation_duration(self) -> int:
        return ANIMATION_DURATION_MS

    def button_for(self, page_name: str) -> QToolButton:
        return self._buttons[page_name]

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(9, 14, 9, 12)
        outer.setSpacing(8)

        brand = QFrame()
        brand.setObjectName("glassBrand")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(6, 4, 6, 4)
        brand_layout.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(46, 46)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(
            logo_pixmap().scaled(
                42,
                42,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._brand_name = QLabel("KMS DTF ERP")
        self._brand_name.setObjectName("glassBrandName")
        self._brand_name.setVisible(False)
        brand_layout.addWidget(icon)
        brand_layout.addWidget(self._brand_name)
        brand_layout.addStretch()
        outer.addWidget(brand)

        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("sidebarContent")
        menu = QVBoxLayout(content)
        menu.setContentsMargins(0, 2, 0, 2)
        menu.setSpacing(5)
        self._add_items(menu, _MAIN_ITEMS)
        divider = QFrame()
        divider.setObjectName("glassDivider")
        divider.setFixedHeight(1)
        menu.addSpacing(4)
        menu.addWidget(divider)
        menu.addSpacing(4)
        self._add_items(menu, _UTILITY_ITEMS)
        menu.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._theme_button = ThemeToggleButton(self._dark_mode)
        self._theme_button.theme_toggled.connect(self._change_theme)
        outer.addWidget(self._theme_button, 0, Qt.AlignmentFlag.AlignHCenter)

    def _add_items(self, layout: QVBoxLayout, items: Sequence[tuple[str, str]]) -> None:
        for page_name, label in items:
            button = GlassNavigationButton(page_name, label)
            if page_name != "users":
                button.clicked.connect(
                    lambda checked=False, name=page_name: self.navigation_requested.emit(name)
                )
            button.hovered.connect(self._button_hovered)
            self._buttons[page_name] = button
            layout.addWidget(button)

    def _button_hovered(self, button: GlassNavigationButton, entered: bool) -> None:
        if entered:
            self._cancel_tooltip_hide()
            self._current_button = button
            self._tooltip.show_for(button, button.label)
        else:
            self._schedule_tooltip_hide()

    def _cancel_tooltip_hide(self) -> None:
        self._tooltip_hide_timer.stop()

    def _schedule_tooltip_hide(self) -> None:
        self._tooltip_hide_timer.start()

    def _tooltip_entered(self) -> None:
        self._cancel_tooltip_hide()
        if self._current_button is not None:
            self._current_button._animate_hover(1.0)

    def _tooltip_left(self) -> None:
        if self._current_button is not None:
            self._current_button._animate_hover(0.0)
        self._schedule_tooltip_hide()

    def _change_theme(self, dark_mode: bool) -> None:
        self._settings.setValue("ui/theme", "dark" if dark_mode else "light")
        self._settings.sync()
        self.set_dark_mode(dark_mode)
        self.theme_changed.emit(dark_mode)

    def set_dark_mode(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self._tooltip.set_dark_mode(dark_mode)
        for button in self._buttons.values():
            button.set_dark_mode(dark_mode)
        self.update()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 25, 25)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if self._dark_mode:
            gradient.setColorAt(0.0, QColor(43, 61, 118, 168))
            gradient.setColorAt(0.55, QColor(40, 60, 111, 150))
            gradient.setColorAt(1.0, QColor(80, 66, 145, 145))
        else:
            gradient.setColorAt(0.0, QColor(235, 244, 255, 215))
            gradient.setColorAt(0.55, QColor(218, 233, 255, 198))
            gradient.setColorAt(1.0, QColor(228, 219, 255, 190))
        painter.fillPath(path, gradient)
        painter.setPen(
            QPen(
                QColor(255, 255, 255, 78) if self._dark_mode else QColor(87, 111, 166, 48),
                1,
            )
        )
        painter.drawPath(path)
        highlight = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        highlight.setColorAt(0, QColor(255, 255, 255, 70))
        highlight.setColorAt(0.55, QColor(255, 255, 255, 8))
        painter.setPen(QPen(highlight, 1.2))
        painter.drawLine(rect.topLeft() + QPoint(4, 22), rect.bottomLeft() + QPoint(4, -22))
        super().paintEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._schedule_tooltip_hide()
        super().leaveEvent(event)

    def expand(self, animated: bool = True) -> None:
        """Compatibility no-op: the navigation rail never expands."""

    def collapse(self, animated: bool = True) -> None:
        """Compatibility no-op: the navigation rail is already collapsed."""

    def set_active_page(self, page_name: str) -> None:
        if page_name not in self._buttons:
            raise KeyError(f"Unknown sidebar page: {page_name}")
        self._active_page = page_name
        for name, button in self._buttons.items():
            button.set_active(name == page_name)

    def set_page_visible(self, page_name: str, visible: bool) -> None:
        self._buttons[page_name].setVisible(visible)
