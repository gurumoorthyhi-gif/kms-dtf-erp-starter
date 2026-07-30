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


def create_gradient_icon(name: str, size: int = 32, *, dark_mode: bool = True) -> QIcon:
    """Create a crisp, theme-aware navigation outline icon."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(QPointF(3, 3), QPointF(size - 3, size - 3))
    if dark_mode:
        gradient.setColorAt(0.0, QColor("#FFFFFF"))
        gradient.setColorAt(0.58, QColor("#E8F1FF"))
        gradient.setColorAt(1.0, QColor("#C9E3FF"))
    else:
        gradient.setColorAt(0.0, QColor("#213765"))
        gradient.setColorAt(0.58, QColor("#344F87"))
        gradient.setColorAt(1.0, QColor("#516EA8"))
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
    elif name in {"orders", "invoices"}:
        painter.drawRoundedRect(
            QRectF(size * 0.25, size * 0.17, size * 0.50, size * 0.66),
            size * 0.06,
            size * 0.06,
        )
        for y in (0.38, 0.52, 0.66):
            painter.drawLine(
                QPointF(size * 0.36, size * y),
                QPointF(size * 0.65, size * y),
            )
    elif name in {"customers", "suppliers"}:
        painter.drawEllipse(QPointF(size * 0.50, size * 0.35), size * 0.13, size * 0.13)
        painter.drawArc(
            QRectF(size * 0.24, size * 0.46, size * 0.52, size * 0.34),
            0,
            180 * 16,
        )
    elif name in {"studio", "artwork", "image_editor"}:
        painter.drawRoundedRect(
            QRectF(size * 0.17, size * 0.20, size * 0.66, size * 0.60),
            size * 0.07,
            size * 0.07,
        )
        painter.drawEllipse(QPointF(size * 0.64, size * 0.36), size * 0.07, size * 0.07)
        path = QPainterPath()
        path.moveTo(size * 0.23, size * 0.69)
        path.lineTo(size * 0.40, size * 0.50)
        path.lineTo(size * 0.52, size * 0.62)
        path.lineTo(size * 0.62, size * 0.52)
        path.lineTo(size * 0.78, size * 0.69)
        painter.drawPath(path)
    elif name in {"inventory", "packing", "products"}:
        painter.drawRoundedRect(
            QRectF(size * 0.19, size * 0.30, size * 0.62, size * 0.47),
            size * 0.05,
            size * 0.05,
        )
        painter.drawLine(QPointF(size * 0.19, size * 0.43), QPointF(size * 0.81, size * 0.43))
        painter.drawLine(QPointF(size * 0.50, size * 0.30), QPointF(size * 0.50, size * 0.77))
    elif name == "purchases":
        painter.drawLine(QPointF(size * 0.18, size * 0.25), QPointF(size * 0.27, size * 0.25))
        painter.drawLine(QPointF(size * 0.27, size * 0.25), QPointF(size * 0.35, size * 0.62))
        painter.drawLine(QPointF(size * 0.35, size * 0.62), QPointF(size * 0.74, size * 0.62))
        painter.drawLine(QPointF(size * 0.32, size * 0.36), QPointF(size * 0.78, size * 0.36))
        painter.drawEllipse(QPointF(size * 0.41, size * 0.74), size * 0.05, size * 0.05)
        painter.drawEllipse(QPointF(size * 0.69, size * 0.74), size * 0.05, size * 0.05)
    elif name == "sales":
        painter.drawPolyline(
            [
                QPointF(size * 0.20, size * 0.68),
                QPointF(size * 0.39, size * 0.49),
                QPointF(size * 0.53, size * 0.60),
                QPointF(size * 0.78, size * 0.31),
            ]
        )
        painter.drawLine(QPointF(size * 0.64, size * 0.31), QPointF(size * 0.78, size * 0.31))
        painter.drawLine(QPointF(size * 0.78, size * 0.31), QPointF(size * 0.78, size * 0.45))
    elif name == "payments":
        painter.drawRoundedRect(
            QRectF(size * 0.14, size * 0.25, size * 0.72, size * 0.51),
            size * 0.08,
            size * 0.08,
        )
        painter.drawLine(QPointF(size * 0.14, size * 0.42), QPointF(size * 0.86, size * 0.42))
        painter.drawLine(QPointF(size * 0.25, size * 0.61), QPointF(size * 0.43, size * 0.61))
    elif name in {"gang_sheets", "ai_tools"}:
        center = QPointF(size / 2, size / 2)
        for angle in (0, 45, 90, 135):
            painter.save()
            painter.translate(center)
            painter.rotate(angle)
            painter.drawLine(QPointF(0, -size * 0.12), QPointF(0, -size * 0.35))
            painter.restore()
        painter.drawEllipse(center, size * 0.08, size * 0.08)
    elif name == "whatsapp":
        painter.drawEllipse(QRectF(size * 0.17, size * 0.16, size * 0.66, size * 0.60))
        painter.drawLine(QPointF(size * 0.28, size * 0.70), QPointF(size * 0.20, size * 0.84))
        painter.drawArc(
            QRectF(size * 0.34, size * 0.31, size * 0.33, size * 0.30),
            205 * 16,
            125 * 16,
        )
    elif name == "email":
        rect = QRectF(size * 0.14, size * 0.24, size * 0.72, size * 0.52)
        painter.drawRoundedRect(rect, size * 0.06, size * 0.06)
        painter.drawLine(rect.topLeft(), QPointF(size * 0.50, size * 0.53))
        painter.drawLine(rect.topRight(), QPointF(size * 0.50, size * 0.53))
    elif name == "cloud_storage":
        path = QPainterPath()
        path.moveTo(size * 0.26, size * 0.70)
        path.cubicTo(
            size * 0.08,
            size * 0.66,
            size * 0.15,
            size * 0.40,
            size * 0.34,
            size * 0.42,
        )
        path.cubicTo(
            size * 0.40,
            size * 0.16,
            size * 0.72,
            size * 0.22,
            size * 0.72,
            size * 0.43,
        )
        path.cubicTo(
            size * 0.91,
            size * 0.45,
            size * 0.88,
            size * 0.70,
            size * 0.70,
            size * 0.70,
        )
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "operations":
        for index, height in enumerate((0.28, 0.48, 0.66)):
            painter.drawRoundedRect(
                QRectF(
                    size * (0.20 + index * 0.21),
                    size * (0.78 - height),
                    size * 0.12,
                    size * height,
                ),
                size * 0.03,
                size * 0.03,
            )
    elif name == "dispatch":
        painter.drawLine(QPointF(size * 0.18, size * 0.50), QPointF(size * 0.78, size * 0.50))
        painter.drawLine(QPointF(size * 0.60, size * 0.31), QPointF(size * 0.79, size * 0.50))
        painter.drawLine(QPointF(size * 0.79, size * 0.50), QPointF(size * 0.60, size * 0.69))
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
