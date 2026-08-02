"""Lazy host and dependency failure UI for WhatsApp WebEngine."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class WhatsAppWorkspaceHost(QWidget):
    """Delay WebEngine initialization until the workspace is actually opened."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loaded = False
        self._layout = QVBoxLayout(self)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._loaded:
            self.load_workspace()

    def load_workspace(self) -> None:
        self._loaded = True
        try:
            from app.modules.whatsapp_workspace.workspace import WhatsAppWorkspace

            self._layout.addWidget(WhatsAppWorkspace(self))
        except (ImportError, OSError, RuntimeError) as error:
            self._show_unavailable(str(error))

    def _show_unavailable(self, detail: str) -> None:
        title = QLabel("WhatsApp Workspace is unavailable")
        title.setObjectName("pageTitle")
        message = QLabel(
            "Qt WebEngine is not installed or could not be loaded. "
            "Install the project dependencies "
            "and restart KMS ERP.\n\n" + detail
        )
        message.setWordWrap(True)
        retry = QPushButton("Retry")
        retry.clicked.connect(self._retry)
        self._layout.addStretch()
        self._layout.addWidget(title)
        self._layout.addWidget(message)
        self._layout.addWidget(retry)
        self._layout.addStretch()

    def _retry(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._loaded = False
        self.load_workspace()
