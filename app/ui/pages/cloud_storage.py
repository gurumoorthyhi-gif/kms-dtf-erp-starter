"""Cloud transfer queue with progress and manual synchronization."""

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.cloud_storage import ALLOWED_PREFIXES, CloudStorageService


class CloudStoragePage(QWidget):
    def __init__(self, service: CloudStorageService, *, auto_refresh: bool = True) -> None:
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        tools = QHBoxLayout()
        self.prefix = QComboBox()
        self.prefix.addItems(ALLOWED_PREFIXES)
        upload, sync = QPushButton("Upload file"), QPushButton("Synchronize")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        tools.addWidget(self.prefix)
        tools.addWidget(upload)
        tools.addWidget(sync)
        tools.addWidget(self.progress)
        layout.addLayout(tools)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["File", "Object key", "Size", "State", "Retries", "Last error"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        upload.clicked.connect(self.upload)
        sync.clicked.connect(self.synchronize)
        if auto_refresh:
            self.refresh()

    def upload(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Upload file")
        if filename:
            self.progress.setValue(0)
            self.service.queue_upload(Path(filename), self.prefix.currentText())
            self.progress.setValue(100)
            self.refresh()

    def synchronize(self) -> None:
        self.progress.setRange(0, 0)
        self.service.synchronize()
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.refresh()

    def refresh(self) -> None:
        files = self.service.list_files()
        self.table.setRowCount(len(files))
        for row, item in enumerate(files):
            values = (
                item.original_name,
                item.object_key,
                str(item.size_bytes),
                item.transfer_state,
                str(item.retry_count),
                item.last_error,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
