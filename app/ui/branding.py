"""Shared access to the KMS DTF ERP brand assets."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


def _asset_path(filename: str) -> Path:
    base_directory = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_directory / "assets" / filename


def application_icon() -> QIcon:
    """Return the transparent application logo as a Qt icon."""

    return QIcon(str(_asset_path("kms_dtf_erp_logo.png")))


def logo_pixmap() -> QPixmap:
    """Return the transparent master logo for in-app branding."""

    return QPixmap(str(_asset_path("kms_dtf_erp_logo.png")))
