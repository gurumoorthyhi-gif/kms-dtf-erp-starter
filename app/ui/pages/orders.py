"""Order intake, customer information, details, and status timeline UI."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
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

from app.modules.customers import CustomerService
from app.modules.orders import (
    ORDER_STATUSES,
    ORDER_TYPES,
    PRIORITIES,
    OrderDetails,
    OrderInput,
    OrderService,
)
from app.modules.products import ProductService

QUICK_ORDER_STATUSES = ("Designing", "Printing", "Completed")


class OrderCreationDialog(QDialog):
    def __init__(
        self,
        customer_service: CustomerService,
        product_service: ProductService | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        del product_service
        self.setWindowTitle("New order")
        self.resize(560, 430)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.customer = QComboBox()
        for customer in customer_service.list_customers():
            self.customer.addItem(customer.display_identifier, customer.id)

        self.order_type = QComboBox()
        self.order_type.addItems(ORDER_TYPES)
        self.priority = QComboBox()
        self.priority.addItems(PRIORITIES)
        self.priority.setCurrentText("Normal")
        self.due_date = QDateEdit(QDate.currentDate())
        self.due_date.setCalendarPopup(True)

        form.addRow("Customer", self.customer)
        form.addRow("Product type", self.order_type)
        form.addRow("Priority", self.priority)
        form.addRow("Due date", self.due_date)
        layout.addLayout(form)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Order notes")
        self.notes.setMaximumHeight(100)
        layout.addWidget(self.notes)
        layout.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def order_input(self) -> OrderInput:
        selected_date = self.due_date.date()
        return OrderInput(
            customer_id=int(self.customer.currentData()),
            order_type=self.order_type.currentText(),
            due_date=date(selected_date.year(), selected_date.month(), selected_date.day()),
            priority=self.priority.currentText(),
            notes=self.notes.toPlainText(),
        )

    def _validate_and_accept(self) -> None:
        if self.customer.currentData() is None:
            QMessageBox.warning(self, "Missing customer", "Select a customer.")
            return
        self.accept()


class OrderDetailsDialog(QDialog):
    def __init__(
        self,
        service: OrderService,
        details: OrderDetails,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.details = details
        self.setWindowTitle(details.summary.order_number)
        self.resize(700, 600)
        self.root_layout = QVBoxLayout(self)
        self._render()

    def _render(self) -> None:
        summary = self.details.summary
        title = QLabel(f"{summary.order_number} · {summary.customer_name}")
        title.setObjectName("detailsTitle")
        self.root_layout.addWidget(title)
        form = QFormLayout()
        for label, value in (
            ("Customer No.", summary.customer_code),
            ("Customer", summary.customer_name),
            ("Product type", summary.order_type),
            ("Status", summary.status),
            ("Priority", summary.priority),
            ("Due date", summary.due_date.isoformat() if summary.due_date else "Not set"),
            ("Notes", self.details.notes or "—"),
        ):
            form.addRow(label, QLabel(value))
        self.root_layout.addLayout(form)

        self.root_layout.addWidget(QLabel("Status timeline"))
        timeline = QListWidget()
        for event in self.details.status_history:
            transition = (
                event.to_status
                if event.from_status is None
                else f"{event.from_status} → {event.to_status}"
            )
            note = f" — {event.note}" if event.note else ""
            timeline.addItem(f"{event.changed_at:%Y-%m-%d %H:%M} · {transition}{note}")
        self.root_layout.addWidget(timeline)

        status_row = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItems(ORDER_STATUSES)
        self.status.setCurrentText(summary.status)
        self.status_note = QLineEdit()
        self.status_note.setPlaceholderText("Status note")
        change = QPushButton("Change status")
        status_row.addWidget(self.status)
        status_row.addWidget(self.status_note, 1)
        status_row.addWidget(change)
        self.root_layout.addLayout(status_row)
        change.clicked.connect(self.change_status)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        self.root_layout.addWidget(close)

    def change_status(self) -> None:
        self.details = self.service.change_status(
            self.details.summary.id,
            self.status.currentText(),
            self.status_note.text(),
        )
        QMessageBox.information(self, "Status updated", "The order status was recorded.")
        self.accept()


class OrdersPage(QWidget):
    order_changed = Signal()

    def __init__(
        self,
        service: OrderService,
        customer_service: CustomerService,
        product_service: ProductService,
        *,
        auto_refresh: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.customer_service = customer_service
        self.product_service = product_service
        self.order_ids: list[int] = []
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search order number or customer")
        new_order = QPushButton("New order")
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(new_order)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Order", "Customer", "Product type", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        view = QPushButton("View order")
        layout.addWidget(view, alignment=Qt.AlignmentFlag.AlignLeft)
        self.search.textChanged.connect(self.refresh)
        new_order.clicked.connect(self.create_order)
        view.clicked.connect(self.view_selected)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.view_selected())
        if auto_refresh:
            self.refresh()

    def _refresh_legacy(self) -> None:
        orders = self.service.list_orders(self.search.text())
        self.order_ids = [order.id for order in orders]
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            for column, value in enumerate(
                (
                    order.order_number,
                    order.customer_code,
                    order.customer_name,
                    order.order_type,
                    order.status,
                    order.priority,
                    order.due_date.isoformat() if order.due_date else "—",
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def refresh(self) -> None:
        orders = self.service.list_orders(self.search.text())
        self.order_ids = [order.id for order in orders]
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            for column, value in enumerate(
                (
                    order.order_number,
                    order.customer_display_identifier,
                    order.order_type,
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
            status = QComboBox()
            if order.status == "Cancelled":
                status.addItem("Canceled", "Cancelled")
                status.setEnabled(False)
            elif order.status in QUICK_ORDER_STATUSES:
                current_index = QUICK_ORDER_STATUSES.index(order.status)
                status.addItem(order.status, order.status)
                for available in QUICK_ORDER_STATUSES[current_index + 1 :]:
                    status.addItem(available, available)
                if order.status == "Completed":
                    status.setEnabled(False)
                else:
                    status.addItem("Canceled", "Cancelled")
            else:
                status.addItem("Select status", "")
                status.addItems(QUICK_ORDER_STATUSES)
                status.addItem("Canceled", "Cancelled")
            status.currentIndexChanged.connect(
                lambda _index, order_id=order.id, control=status: self._set_quick_status(
                    order_id,
                    control,
                )
            )
            self.table.setCellWidget(row, 3, status)

    def _set_quick_status(self, order_id: int, control: QComboBox) -> None:
        status = control.currentData() or control.currentText()
        if status not in (*QUICK_ORDER_STATUSES, "Cancelled"):
            return
        try:
            self.service.change_status(order_id, status)
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Status not updated", str(error))
            return
        self.order_changed.emit()

    def create_order(self) -> None:
        dialog = OrderCreationDialog(self.customer_service, self.product_service, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            details = self.service.create_order(dialog.order_input())
        except (ValueError, LookupError) as error:
            QMessageBox.warning(self, "Order not created", str(error))
            return
        self.refresh()
        self.order_changed.emit()
        OrderDetailsDialog(self.service, details, self).exec()

    def view_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.order_ids):
            return
        details = self.service.get_order(self.order_ids[row])
        OrderDetailsDialog(self.service, details, self).exec()
        self.refresh()
        self.order_changed.emit()
