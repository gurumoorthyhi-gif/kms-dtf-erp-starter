"""Guarded WebEngine page and view."""

from __future__ import annotations

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.modules.whatsapp_workspace.navigation_guard import redact_url, top_level_url_is_allowed


class GuardedWhatsAppPage(QWebEnginePage):
    external_navigation_requested = Signal(QUrl, str)

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):  # noqa: N802
        if not is_main_frame or top_level_url_is_allowed(url.toString()):
            return True
        self.external_navigation_requested.emit(url, redact_url(url.toString()))
        return False


class WhatsAppWebView(QWebEngineView):
    def __init__(self, profile, parent=None) -> None:
        super().__init__(parent)
        self.setPage(GuardedWhatsAppPage(profile, self))

