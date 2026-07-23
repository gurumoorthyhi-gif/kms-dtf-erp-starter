"""Artwork library, upload, optimized preview, and version UI."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.modules.artwork import APPROVAL_STATUSES, ArtworkDetails, ArtworkInput, ArtworkService
from app.modules.customers import CustomerService
from app.modules.orders import OrderService

IMAGE_FILTER = "Artwork (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp)"


class ArtworkUploadDialog(QDialog):
    def __init__(
        self,
        customer_service: CustomerService,
        order_service: OrderService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upload artwork")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title = QLineEdit()
        self.source = QLineEdit()
        browse = QPushButton("Browse")
        source_row = QHBoxLayout()
        source_row.addWidget(self.source, 1)
        source_row.addWidget(browse)
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("logo, customer, repeat-order")
        self.customer = QComboBox()
        self.customer.addItem("Not linked", None)
        for customer in customer_service.list_customers():
            self.customer.addItem(f"{customer.code} - {customer.name}", customer.id)
        self.order = QComboBox()
        self.order.addItem("Not linked", None)
        for order in order_service.list_orders():
            self.order.addItem(
                f"{order.order_number} - {order.customer_name}",
                order.id,
            )
        form.addRow("Title", self.title)
        form.addRow("File", source_row)
        form.addRow("Tags", self.tags)
        form.addRow("Customer", self.customer)
        form.addRow("Order", self.order)
        layout.addLayout(form)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Version notes")
        layout.addWidget(self.notes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        browse.clicked.connect(self._browse)

    def value(self) -> ArtworkInput:
        return ArtworkInput(
            title=self.title.text(),
            source_path=Path(self.source.text()),
            tags=tuple(self.tags.text().split(",")),
            customer_id=self.customer.currentData(),
            order_id=self.order.currentData(),
            notes=self.notes.toPlainText(),
        )

    def _browse(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Select artwork", "", IMAGE_FILTER)
        if selected:
            self.source.setText(selected)
            if not self.title.text():
                self.title.setText(Path(selected).stem)

    def _accept_if_valid(self) -> None:
        if not self.title.text().strip() or not Path(self.source.text()).is_file():
            QMessageBox.warning(self, "Missing artwork", "Select a file and enter a title.")
            return
        self.accept()


class ArtworkDetailsDialog(QDialog):
    def __init__(
        self,
        service: ArtworkService,
        details: ArtworkDetails,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.details = details
        self.setWindowTitle(details.summary.title)
        self.resize(760, 720)
        layout = QVBoxLayout(self)
        latest = details.summary.latest_version
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(260)
        pixmap = QPixmap(str(service.preview_file(latest.preview_path)))
        self.preview.setPixmap(
            pixmap.scaled(
                600,
                360,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(self.preview)
        form = QFormLayout()
        for label, value in (
            ("Title", details.summary.title),
            ("Tags", ", ".join(details.summary.tags) or "—"),
            ("Customer", details.summary.customer_name or "—"),
            ("Order", details.summary.order_number or "—"),
            ("Version", str(latest.version_number)),
            ("Original file", latest.original_filename),
            ("Resolution", f"{latest.width} × {latest.height} px"),
            ("DPI", f"{latest.dpi_x} × {latest.dpi_y}"),
            ("Transparency", "Yes" if latest.has_transparency else "No"),
            ("Approval", latest.approval_status),
        ):
            form.addRow(label, QLabel(value))
        layout.addLayout(form)
        layout.addWidget(QLabel("Versions"))
        versions = QListWidget()
        for version in reversed(details.versions):
            versions.addItem(
                f"v{version.version_number} · {version.original_filename} · "
                f"{version.width}×{version.height} · {version.approval_status}"
            )
        layout.addWidget(versions)
        actions = QHBoxLayout()
        new_version = QPushButton("Add version")
        self.approval = QComboBox()
        self.approval.addItems(APPROVAL_STATUSES)
        approval_button = QPushButton("Record approval")
        actions.addWidget(new_version)
        actions.addStretch()
        actions.addWidget(self.approval)
        actions.addWidget(approval_button)
        layout.addLayout(actions)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        new_version.clicked.connect(self.add_version)
        approval_button.clicked.connect(self.record_approval)

    def add_version(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Select new version", "", IMAGE_FILTER)
        if not selected:
            return
        self.details = self.service.add_version(self.details.summary.id, Path(selected))
        QMessageBox.information(self, "Version added", "A new artwork version was created.")
        self.accept()

    def record_approval(self) -> None:
        latest = self.details.summary.latest_version
        self.details = self.service.record_approval(latest.id, self.approval.currentText())
        QMessageBox.information(self, "Approval recorded", "The decision was saved.")
        self.accept()


class ArtworkLibraryPage(QWidget):
    def __init__(
        self,
        service: ArtworkService,
        customer_service: CustomerService,
        order_service: OrderService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.customer_service = customer_service
        self.order_service = order_service
        self.artwork_ids: list[int] = []
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, tags, customer, or order")
        upload = QPushButton("Upload artwork")
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(upload)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Artwork", "Tags", "Customer", "Order", "Version", "Resolution", "Approval"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        view = QPushButton("View artwork")
        layout.addWidget(view, alignment=Qt.AlignmentFlag.AlignLeft)
        self.search.textChanged.connect(self.refresh)
        upload.clicked.connect(self.upload)
        view.clicked.connect(self.view_selected)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.view_selected())
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        artwork = self.service.list_artwork(self.search.text())
        self.artwork_ids = [item.id for item in artwork]
        self.table.setRowCount(len(artwork))
        for row, item in enumerate(artwork):
            latest = item.latest_version
            values = (
                item.title,
                ", ".join(item.tags),
                item.customer_name,
                item.order_number,
                f"v{latest.version_number}",
                f"{latest.width}×{latest.height}",
                latest.approval_status,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def upload(self) -> None:
        dialog = ArtworkUploadDialog(self.customer_service, self.order_service, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            details = self.service.upload(dialog.value())
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Upload failed", str(error))
            return
        self.refresh()
        ArtworkDetailsDialog(self.service, details, self).exec()

    def view_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.artwork_ids):
            return
        details = self.service.get_artwork(self.artwork_ids[row])
        ArtworkDetailsDialog(self.service, details, self).exec()
        self.refresh()
