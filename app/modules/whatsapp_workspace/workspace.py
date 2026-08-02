"""Phase 1 embedded WhatsApp Web workspace UI."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.modules.whatsapp_workspace.constants import WHATSAPP_HOME_URL
from app.modules.whatsapp_workspace.profile import (
    WhatsAppProfilePaths,
    create_profile,
)
from app.modules.whatsapp_workspace.web_view import WhatsAppWebView


class WhatsAppWorkspace(QWidget):
    """A persistent, guarded WhatsApp Web browser inside the ERP shell."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._profile_paths = WhatsAppProfilePaths.default()
        self._profile = create_profile(self, self._profile_paths)
        self._view = WhatsAppWebView(self._profile, self)
        self._view.setZoomFactor(1.15)
        self._build_ui()
        self._connect_signals()
        self._view.setUrl(QUrl(WHATSAPP_HOME_URL))

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        controls = (
            ("Back", self._view.back),
            ("Forward", self._view.forward),
            ("Refresh", self._view.reload),
            ("WhatsApp Home", lambda: self._view.setUrl(QUrl(WHATSAPP_HOME_URL))),
            ("Open externally", self._open_current_externally),
            ("Full screen", self._toggle_full_screen),
            ("Show/Hide ERP panel", self._toggle_erp_panel),
            ("Clear session", self._confirm_clear_session),
        )
        for text, callback in controls:
            button = QPushButton(text)
            button.setObjectName("secondaryButton")
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch()
        root.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(8)
        self._erp_panel = QFrame()
        self._erp_panel.setObjectName("glassCard")
        self._erp_panel.setMinimumWidth(210)
        self._erp_panel.setMaximumWidth(290)
        self._erp_panel.setVisible(False)
        panel_layout = QVBoxLayout(self._erp_panel)
        title = QLabel("WhatsApp Workspace")
        title.setObjectName("cardTitle")
        panel_layout.addWidget(title)
        panel_layout.addWidget(
            QLabel("Your WhatsApp login is stored only in this Windows user profile.")
        )
        panel_layout.addStretch()
        self._connection = QLabel("Connecting…")
        panel_layout.addWidget(self._connection)
        body.addWidget(self._erp_panel)
        body.addWidget(self._view, 1)
        root.addLayout(body, 1)

        status = QHBoxLayout()
        self._status = QLabel("Loading WhatsApp Web…")
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setMaximumWidth(220)
        status.addWidget(self._status, 1)
        status.addWidget(self._progress)
        root.addLayout(status)

    def _connect_signals(self) -> None:
        self._view.loadStarted.connect(self._load_started)
        self._view.loadProgress.connect(self._progress.setValue)
        self._view.loadFinished.connect(self._load_finished)
        self._view.titleChanged.connect(self._title_changed)
        self._view.page().external_navigation_requested.connect(self._confirm_external_navigation)

    def _load_started(self) -> None:
        self._status.setText("Loading WhatsApp Web…")
        self._connection.setText("Connecting…")
        self._progress.show()

    def _load_finished(self, succeeded: bool) -> None:
        self._progress.hide()
        self._connection.setText("Online" if succeeded else "Unable to connect")
        self._status.setText("WhatsApp Web ready" if succeeded else "WhatsApp Web failed to load")

    def _title_changed(self, title: str) -> None:
        if title:
            self._status.setText(title)

    def _toggle_erp_panel(self) -> None:
        self._erp_panel.setVisible(not self._erp_panel.isVisible())

    def _toggle_full_screen(self) -> None:
        window = self.window()
        window.showNormal() if window.isFullScreen() else window.showFullScreen()

    def _open_current_externally(self) -> None:
        self._confirm_external_navigation(self._view.url(), self._view.url().host())

    def _confirm_external_navigation(self, url: QUrl, safe_url: str) -> None:
        choice = QMessageBox.warning(
            self,
            "Open outside KMS ERP?",
            f"This link will leave the protected WhatsApp workspace:\n\n{safe_url}",
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Open:
            QDesktopServices.openUrl(url)

    def _confirm_clear_session(self) -> None:
        choice = QMessageBox.warning(
            self,
            "Clear WhatsApp session?",
            "This removes saved cookies and browser cache. "
            "You will need to scan the WhatsApp QR code again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        self._view.page().runJavaScript(
            """
            localStorage.clear();
            sessionStorage.clear();
            if (window.caches) {
                caches.keys().then(keys => keys.forEach(key => caches.delete(key)));
            }
            if (navigator.serviceWorker) {
                navigator.serviceWorker.getRegistrations().then(
                    registrations => registrations.forEach(item => item.unregister())
                );
            }
            if (indexedDB.databases) {
                indexedDB.databases().then(
                    databases => databases.forEach(
                        database => database.name && indexedDB.deleteDatabase(database.name)
                    )
                );
            }
            """
        )
        self._profile.cookieStore().deleteAllCookies()
        self._profile.clearHttpCache()
        self._view.setUrl(QUrl(WHATSAPP_HOME_URL))
        self._status.setText("Session cleared; reload and scan the QR code")
