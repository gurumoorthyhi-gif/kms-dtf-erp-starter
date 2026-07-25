"""Code-painted gradient icons for the application shell."""

from __future__ import annotations

import sys
from pathlib import Path

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


def create_navigation_icon(name: str) -> QIcon:
    """Load the supplied scalable navigation artwork with painted fallback."""

    aliases = {
        "studio": "artwork",
        "sales": "invoices",
        "operations": "reports",
    }
    asset_name = aliases.get(name, name)
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    asset = bundle_root / "assets" / "icons" / "navigation" / f"{asset_name}.png"
    if asset.is_file():
        return QIcon(str(asset))
    return create_gradient_icon(name)


def create_brand_logo() -> QIcon:
    """Load the supplied KMS logo with a painted fallback."""

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    asset = bundle_root / "assets" / "branding" / "kms-logo.png"
    if asset.is_file():
        return QIcon(str(asset))
    return create_gradient_icon("brand", 48)


def create_sidebar_toggle_icon(expanded: bool, size: int = 18) -> QIcon:
    """Paint a precisely centered expand/collapse chevron."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(QPointF(3, 3), QPointF(size - 3, size - 3))
    gradient.setColorAt(0.0, QColor("#6C5CE7"))
    gradient.setColorAt(0.55, QColor("#4F7CFF"))
    gradient.setColorAt(1.0, QColor("#42D3FF"))
    pen = QPen(gradient, 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    direction = -1 if expanded else 1
    for center_x in (size * 0.40, size * 0.62):
        outer_x = center_x - direction * size * 0.16
        painter.drawPolyline(
            (
                QPointF(outer_x, size * 0.25),
                QPointF(center_x, size * 0.50),
                QPointF(outer_x, size * 0.75),
            )
        )
    painter.end()
    return QIcon(pixmap)


def create_sidebar_navigation_icon(name: str, size: int = 38) -> QIcon:
    """Build the reference-style gradient tile with a white symbol."""

    accent_pairs = {
        "dashboard": ("#825CFF", "#5D7CFF"),
        "orders": ("#6372E8", "#5786F3"),
        "customers": ("#527DEB", "#45A5F5"),
        "artwork": ("#5C8EEF", "#42BCEB"),
        "studio": ("#5C8EEF", "#42BCEB"),
        "production": ("#498DDC", "#54B9DE"),
        "inventory": ("#5A7EDF", "#61A6ED"),
        "purchases": ("#A354DB", "#C05BD5"),
        "sales": ("#C256D0", "#8B67EE"),
        "invoices": ("#6969E9", "#668DF5"),
        "payments": ("#7476EB", "#8797F5"),
        "whatsapp": ("#2CBF8A", "#4CD6A3"),
        "email": ("#4289E8", "#52AAF4"),
        "settings": ("#8595D8", "#A8B7E8"),
    }
    start, end = accent_pairs.get(name, ("#6574DF", "#6D8DF1"))
    tile = QPixmap(size, size)
    tile.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tile)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(QPointF(0, 0), QPointF(size, size))
    gradient.setColorAt(0.0, QColor(start))
    gradient.setColorAt(1.0, QColor(end))
    painter.setPen(QPen(QColor(255, 255, 255, 65), 1))
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 9, 9)

    symbol_size = round(size * 0.58)
    source = create_navigation_icon(name).pixmap(symbol_size, symbol_size)
    white_symbol = QPixmap(source.size())
    white_symbol.fill(Qt.GlobalColor.transparent)
    symbol_painter = QPainter(white_symbol)
    symbol_painter.drawPixmap(0, 0, source)
    symbol_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    symbol_painter.fillRect(white_symbol.rect(), QColor("#F7FAFF"))
    symbol_painter.end()
    offset = (size - symbol_size) // 2
    painter.drawPixmap(offset, offset, white_symbol)
    painter.end()
    return QIcon(tile)
