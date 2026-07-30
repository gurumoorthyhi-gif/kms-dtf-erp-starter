"""Storage and backup settings."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.modules.cloud_storage import (
    BackblazeConfiguration,
    CloudStorageService,
    S3CompatibleProvider,
    StorageConfigurationStore,
)


class SettingsPage(QWidget):
    """Configure private Backblaze storage and optional Drive catalog entries."""

    storage_changed = Signal()

    def __init__(
        self,
        storage_service: CloudStorageService | None = None,
        configuration_store: StorageConfigurationStore | None = None,
        google_sync=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = storage_service
        self._store = configuration_store
        self._google_sync = google_sync

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("glassCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(14)

        title = QLabel("Private file storage")
        title.setObjectName("cardTitle")
        description = QLabel(
            "Backblaze B2 stores the original files. The ERP keeps a local cache "
            "and safely queues uploads whenever the internet is unavailable."
        )
        description.setObjectName("cardBody")
        description.setWordWrap(True)
        card_layout.addWidget(title)
        card_layout.addWidget(description)

        form = QFormLayout()
        self.endpoint = QLineEdit()
        self.endpoint.setPlaceholderText("https://s3.<region>.backblazeb2.com")
        self.bucket = QLineEdit()
        self.bucket.setPlaceholderText("Private bucket name")
        self.key_id = QLineEdit()
        self.key_id.setPlaceholderText("Backblaze application key ID")
        self.application_key = QLineEdit()
        self.application_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.application_key.setPlaceholderText("Leave blank to keep saved key")
        form.addRow("S3 endpoint", self.endpoint)
        form.addRow("Bucket", self.bucket)
        form.addRow("Key ID", self.key_id)
        form.addRow("Application key", self.application_key)
        card_layout.addLayout(form)

        self.google_catalog = QCheckBox(
            "Google Drive catalog sync (managed by the universal Drive button)"
        )
        self.google_catalog.setToolTip(
            "Files remain private in Backblaze; Google Drive stores metadata-only entries."
        )
        card_layout.addWidget(self.google_catalog)
        self.google_catalog.setEnabled(False)

        buttons = QHBoxLayout()
        self.test_button = QPushButton("Test connection")
        self.save_button = QPushButton("Save storage settings")
        buttons.addWidget(self.test_button)
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        card_layout.addLayout(buttons)

        self.status = QLabel()
        self.status.setObjectName("cardBody")
        self.status.setWordWrap(True)
        card_layout.addWidget(self.status)
        layout.addWidget(card)
        layout.addStretch()

        self.test_button.clicked.connect(self.test_connection)
        self.save_button.clicked.connect(self.save)
        self._load()

    def _load(self) -> None:
        if self._store is None:
            self._set_available(False, "Storage configuration is unavailable.")
            return
        config, secret = self._store.load()
        self.endpoint.setText(config.endpoint_url)
        self.bucket.setText(config.bucket)
        self.key_id.setText(config.key_id)
        self.application_key.setText(secret)
        self.google_catalog.setChecked(
            bool(self._google_sync is not None and self._google_sync.is_connected)
        )
        self.status.setText(
            "Backblaze is configured."
            if config.is_configured and secret
            else "Enter the private Backblaze bucket connection details."
        )

    def _configuration(self) -> BackblazeConfiguration:
        return BackblazeConfiguration(
            endpoint_url=self.endpoint.text().strip(),
            bucket=self.bucket.text().strip(),
            key_id=self.key_id.text().strip(),
            google_catalog_enabled=bool(
                self._google_sync is not None and self._google_sync.is_connected
            ),
        )

    def _provider(self) -> S3CompatibleProvider:
        if self._store is None:
            raise RuntimeError("Storage configuration is unavailable")
        config = self._configuration()
        _, saved_secret = self._store.load()
        secret = self.application_key.text() or saved_secret
        return S3CompatibleProvider.for_backblaze(
            endpoint_url=config.endpoint_url,
            key_id=config.key_id,
            application_key=secret,
            bucket=config.bucket,
        )

    def test_connection(self) -> None:
        try:
            online = self._provider().is_online()
        except Exception as error:
            self.status.setText(f"Connection failed: {error}")
            return
        self.status.setText(
            "Connection successful. The private bucket is ready."
            if online
            else "Connection failed. Check the endpoint, bucket, and application key."
        )

    def save(self) -> None:
        if self._store is None or self._service is None:
            return
        try:
            config = self._configuration()
            provider = self._provider()
            if not provider.is_online():
                raise RuntimeError("Backblaze did not accept these connection details")
            callback = None
            if self._google_sync is not None and self._google_sync.is_connected:
                callback = self._google_sync.create_storage_catalog_entry
            self._store.save(config, self.application_key.text())
            self._service.set_provider(provider)
            self._service.set_upload_completed_callback(callback)
            self.application_key.clear()
            self.status.setText("Saved. New and queued files will use private Backblaze storage.")
            self.storage_changed.emit()
        except Exception as error:
            QMessageBox.warning(self, "Storage settings", str(error))

    def _set_available(self, enabled: bool, message: str) -> None:
        for widget in (
            self.endpoint,
            self.bucket,
            self.key_id,
            self.application_key,
            self.google_catalog,
            self.test_button,
            self.save_button,
        ):
            widget.setEnabled(enabled)
        self.status.setText(message)
