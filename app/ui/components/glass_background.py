"""Custom-painted gradient backdrop for the glass application shell."""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget


class GlassApplicationBackground(QWidget):
    """Paint a band-free navy, blue and violet background with soft light pools."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme_progress = 0.0
        self._theme_animation = QPropertyAnimation(self, b"themeProgress", self)
        self._theme_animation.setDuration(350)
        self._theme_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_theme_progress(self) -> float:
        return self._theme_progress

    def set_theme_progress(self, value: float) -> None:
        self._theme_progress = value
        self.update()

    themeProgress = Property(float, get_theme_progress, set_theme_progress)

    def set_dark_mode(self, dark_mode: bool, animated: bool = True) -> None:
        target = 0.0 if dark_mode else 1.0
        self._theme_animation.stop()
        if not animated:
            self.set_theme_progress(target)
            return
        self._theme_animation.setStartValue(self._theme_progress)
        self._theme_animation.setEndValue(target)
        self._theme_animation.start()

    def _mix(self, dark: str, light: str) -> QColor:
        start = QColor(dark)
        end = QColor(light)
        value = self._theme_progress
        return QColor(
            round(start.red() + ((end.red() - start.red()) * value)),
            round(start.green() + ((end.green() - start.green()) * value)),
            round(start.blue() + ((end.blue() - start.blue()) * value)),
        )

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())

        base = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        base.setColorAt(0.0, self._mix("#101A47", "#F4F8FF"))
        base.setColorAt(0.55, self._mix("#315B98", "#DCEAFF"))
        base.setColorAt(1.0, self._mix("#7798D5", "#D8D2F4"))
        painter.fillRect(rect, base)

        blue = QRadialGradient(
            QPointF(rect.width() * 0.18, rect.height() * 0.80),
            rect.width() * 0.42,
        )
        blue.setColorAt(0.0, QColor(75, 145, 255, round(75 - 30 * self._theme_progress)))
        blue.setColorAt(1.0, QColor(75, 145, 255, 0))
        painter.fillRect(rect, blue)

        violet = QRadialGradient(
            QPointF(rect.width() * 0.82, rect.height() * 0.90),
            rect.width() * 0.38,
        )
        violet.setColorAt(0.0, QColor(165, 108, 255, round(70 - 20 * self._theme_progress)))
        violet.setColorAt(1.0, QColor(155, 110, 255, 0))
        painter.fillRect(rect, violet)

        rail_shadow = QRadialGradient(
            QPointF(rect.width() * 0.03, rect.height() * 0.50),
            rect.width() * 0.23,
        )
        rail_shadow.setColorAt(0.0, QColor(5, 15, 55, round(90 - 65 * self._theme_progress)))
        rail_shadow.setColorAt(1.0, QColor(5, 15, 55, 0))
        painter.fillRect(rect, rail_shadow)
