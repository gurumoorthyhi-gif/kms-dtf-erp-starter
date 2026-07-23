"""Code-painted gradient icons for the application shell."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


def create_gradient_icon(name: str, size: int = 32) -> QIcon:
    """Create a crisp purple-blue-cyan navigation icon."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(QPointF(3, 3), QPointF(size - 3, size - 3))
    gradient.setColorAt(0.0, QColor("#6C5CE7"))
    gradient.setColorAt(0.55, QColor("#4F7CFF"))
    gradient.setColorAt(1.0, QColor("#42D3FF"))
    pen = QPen(gradient, max(2.0, size / 12))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "dashboard":
        gap = size * 0.10
        tile = size * 0.27
        offset = size * 0.18
        for row in range(2):
            for column in range(2):
                painter.drawRoundedRect(
                    QRectF(
                        offset + column * (tile + gap),
                        offset + row * (tile + gap),
                        tile,
                        tile,
                    ),
                    size * 0.06,
                    size * 0.06,
                )
    elif name == "settings":
        center = QPointF(size / 2, size / 2)
        painter.drawEllipse(center, size * 0.12, size * 0.12)
        painter.drawEllipse(center, size * 0.28, size * 0.28)
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(center)
            painter.rotate(angle)
            painter.drawLine(QPointF(0, -size * 0.30), QPointF(0, -size * 0.40))
            painter.restore()
    else:
        path = QPainterPath()
        path.moveTo(size * 0.22, size * 0.70)
        path.lineTo(size * 0.22, size * 0.30)
        path.lineTo(size * 0.78, size * 0.30)
        path.lineTo(size * 0.78, size * 0.70)
        path.closeSubpath()
        painter.drawPath(path)

    painter.end()
    return QIcon(pixmap)
