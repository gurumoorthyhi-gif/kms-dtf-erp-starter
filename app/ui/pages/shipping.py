"""Packing and dispatch workspace pages."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.modules.orders import OrderService
from app.modules.shipping import (
    DELIVERY_STATUSES,
    DispatchInput,
    DispatchService,
    PackingInput,
    PackingService,
)


class PackingPage(QWidget):
    def __init__(
        self, service: PackingService, orders: OrderService, *, auto_refresh: bool = True
    ) -> None:
        super().__init__()
        self.service, self.orders = service, orders
        self.ids: list[int] = []
        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        self.order = QComboBox()
        self.count, self.weight = QLineEdit("1"), QLineEdit("0")
        create, complete = QPushButton("Create packing"), QPushButton("Mark complete")
        for widget in (self.order, self.count, self.weight, create, complete):
            form.addWidget(widget)
        layout.addLayout(form)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Packing", "Order", "Customer", "Packages", "Weight", "Complete", "Packing list"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        create.clicked.connect(self.create_packing)
        complete.clicked.connect(self.complete)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        self.order.clear()
        for order in self.orders.list_orders():
            self.order.addItem(f"{order.order_number} · {order.customer_name}", order.id)
        packings = self.service.list()
        self.ids = [item.id for item in packings]
        self.table.setRowCount(len(packings))
        for row, item in enumerate(packings):
            values = (
                item.packing_number,
                item.order_number,
                item.customer_name,
                str(item.package_count),
                str(item.package_weight),
                "Yes" if item.is_complete else "No",
                item.packing_list.replace("\n", "; "),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def create_packing(self) -> None:
        if self.order.currentData() is None:
            return
        try:
            self.service.create(
                PackingInput(
                    int(self.order.currentData()),
                    int(self.count.text()),
                    Decimal(self.weight.text()),
                )
            )
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, "Packing failed", str(error))
        self.refresh()

    def complete(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.ids):
            self.service.complete(self.ids[row])
            self.refresh()


class DispatchPage(QWidget):
    def __init__(
        self,
        service: DispatchService,
        packing: PackingService,
        *,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.service, self.packing = service, packing
        self.ids: list[int] = []
        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        self.packing_record = QComboBox()
        self.courier = QComboBox()
        self.courier.addItems(("Blue Dart", "Delhivery", "DTDC", "India Post", "Other"))
        self.tracking = QLineEdit()
        self.tracking.setPlaceholderText("Tracking number")
        self.proof = QLineEdit()
        self.proof.setPlaceholderText("Proof-of-dispatch file")
        browse = QPushButton("Browse")
        self.override = QCheckBox("Authorized override")
        create = QPushButton("Create dispatch")
        for widget in (
            self.packing_record,
            self.courier,
            self.tracking,
            self.proof,
            browse,
            self.override,
            create,
        ):
            form.addWidget(widget)
        layout.addLayout(form)
        actions = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItems(DELIVERY_STATUSES)
        update, label = QPushButton("Update delivery"), QPushButton("Export label")
        actions.addWidget(self.status)
        actions.addWidget(update)
        actions.addWidget(label)
        layout.addLayout(actions)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Dispatch", "Order", "Customer", "Courier", "Tracking", "Date", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        browse.clicked.connect(self.browse)
        create.clicked.connect(self.create_dispatch)
        update.clicked.connect(self.update_delivery)
        label.clicked.connect(self.export_label)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        self.packing_record.clear()
        for packing in self.packing.list():
            self.packing_record.addItem(
                f"{packing.packing_number} · {packing.order_number}", packing.id
            )
        dispatches = self.service.list()
        self.ids = [item.id for item in dispatches]
        self.table.setRowCount(len(dispatches))
        for row, item in enumerate(dispatches):
            values = (
                item.dispatch_number,
                item.order_number,
                item.customer_name,
                item.courier,
                item.tracking_number,
                item.dispatch_date.isoformat(),
                item.delivery_status,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def browse(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Select proof of dispatch")
        if filename:
            self.proof.setText(filename)

    def create_dispatch(self) -> None:
        if self.packing_record.currentData() is None:
            return
        try:
            self.service.create(
                DispatchInput(
                    int(self.packing_record.currentData()),
                    self.courier.currentText(),
                    self.tracking.text(),
                    self.proof.text(),
                    self.override.isChecked(),
                )
            )
        except ValueError as error:
            QMessageBox.warning(self, "Dispatch failed", str(error))
        self.refresh()

    def update_delivery(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.ids):
            self.service.update_delivery(self.ids[row], self.status.currentText())
            self.refresh()

    def export_label(self) -> None:
        row = self.table.currentRow()
        if not 0 <= row < len(self.ids):
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export shipping label", "shipping-label.pdf", "PDF (*.pdf)"
        )
        if filename:
            self.service.export_shipping_label(self.ids[row], Path(filename))
