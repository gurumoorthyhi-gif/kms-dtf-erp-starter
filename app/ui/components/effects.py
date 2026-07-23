"""Reusable visual effects."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_soft_shadow(widget: QWidget) -> None:
    """Apply a subtle floating-card shadow."""

    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(34)
    shadow.setColor(QColor(63, 76, 130, 35))
    shadow.setOffset(0, 8)
    widget.setGraphicsEffect(shadow)
