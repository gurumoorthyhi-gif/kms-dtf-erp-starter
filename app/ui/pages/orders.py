"""Order list, creation, details, and status timeline UI."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
    PRIORITIES,
    OrderDetails,
    OrderInput,
    OrderItemInput,
    OrderService,
)
from app.modules.products import ProductService


class OrderCreationDialog(QDialog):
    def __init__(
        self,
        customer_service: CustomerService,
        product_service: ProductService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New order")
        self.resize(620, 620)
        self._items: list[OrderItemInput] = []
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.customer = QComboBox()
        for customer in customer_service.list_customers():
            self.customer.addItem(f"{customer.code} - {customer.name}", customer.id)
        self.priority = QComboBox()
        self.priority.addItems(PRIORITIES)
        self.priority.setCurrentText("Normal")
        self.has_due_date = QCheckBox("Set due date")
        self.due_date = QDateEdit(QDate.currentDate())
        self.due_date.setCalendarPopup(True)
        self.due_date.setEnabled(False)
        self.has_due_date.toggled.connect(self.due_date.setEnabled)
        self.advance = QLineEdit("0.00")
        form.addRow("Customer", self.customer)
        form.addRow("Priority", self.priority)
        form.addRow(self.has_due_date, self.due_date)
        form.addRow("Advance", self.advance)
        layout.addLayout(form)

        item_row = QHBoxLayout()
        self.product = QComboBox()
        for product in product_service.list_products():
            self.product.addItem(f"{product.code} - {product.name}", product.id)
        self.quantity = QLineEdit("1")
        add_item = QPushButton("Add item")
        item_row.addWidget(self.product, 1)
        item_row.addWidget(self.quantity)
        item_row.addWidget(add_item)
        layout.addLayout(item_row)
        self.item_list = QListWidget()
        layout.addWidget(self.item_list, 1)
        add_item.clicked.connect(self.add_item)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Order notes")
        self.notes.setMaximumHeight(90)
        layout.addWidget(self.notes)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_item(self) -> None:
        product_id = self.product.currentData()
        try:
            quantity = Decimal(self.quantity.text())
        except InvalidOperation:
            QMessageBox.warning(self, "Invalid quantity", "Enter a valid numeric quantity.")
            return
        if product_id is None or quantity <= 0:
            QMessageBox.warning(self, "Invalid item", "Select a product and positive quantity.")
            return
        self._items.append(OrderItemInput(int(product_id), quantity))
        self.item_list.addItem(f"{self.product.currentText()} × {quantity}")

    def order_input(self) -> OrderInput:
        selected_date = self.due_date.date()
        due_date = (
            date(selected_date.year(), selected_date.month(), selected_date.day())
            if self.has_due_date.isChecked()
            else None
        )
        return OrderInput(
            customer_id=int(self.customer.currentData()),
            items=tuple(self._items),
            advance=Decimal(self.advance.text()),
            due_date=due_date,
            priority=self.priority.currentText(),
            notes=self.notes.toPlainText(),
        )

    def _validate_and_accept(self) -> None:
        if not self._items:
            QMessageBox.warning(self, "Missing items", "Add at least one item to the order.")
            return
        try:
            Decimal(self.advance.text())
        except InvalidOperation:
            QMessageBox.warning(self, "Invalid advance", "Enter a valid advance amount.")
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
        self.resize(700, 680)
        self.root_layout = QVBoxLayout(self)
        self._render()

    def _render(self) -> None:
        summary = self.details.summary
        title = QLabel(f"{summary.order_number} · {summary.customer_name}")
        title.setObjectName("detailsTitle")
        self.root_layout.addWidget(title)
        form = QFormLayout()
        for label, value in (
            ("Status", summary.status),
            ("Priority", summary.priority),
            ("Due date", summary.due_date.isoformat() if summary.due_date else "Not set"),
            ("Subtotal", str(self.details.subtotal)),
            ("Discount", str(self.details.discount)),
            ("Tax", str(self.details.tax)),
            ("Total", str(summary.total)),
            ("Advance", str(self.details.advance)),
            ("Balance", str(summary.balance)),
            ("Notes", self.details.notes or "—"),
        ):
            form.addRow(label, QLabel(value))
        self.root_layout.addLayout(form)

        self.root_layout.addWidget(QLabel("Items"))
        items = QTableWidget(len(self.details.items), 4)
        items.setHorizontalHeaderLabels(["Description", "Quantity", "Unit price", "Total"])
        items.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for row, item in enumerate(self.details.items):
            for column, value in enumerate(
                (item.description, str(item.quantity), str(item.unit_price), str(item.total))
            ):
                items.setItem(row, column, QTableWidgetItem(value))
        self.root_layout.addWidget(items)

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
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Order", "Customer", "Status", "Priority", "Due date", "Total", "Balance"]
        )
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

    def refresh(self) -> None:
        orders = self.service.list_orders(self.search.text())
        self.order_ids = [order.id for order in orders]
        self.table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            for column, value in enumerate(
                (
                    order.order_number,
                    order.customer_name,
                    order.status,
                    order.priority,
                    order.due_date.isoformat() if order.due_date else "—",
                    str(order.total),
                    str(order.balance),
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))

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
        OrderDetailsDialog(self.service, details, self).exec()

    def view_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.order_ids):
            return
        details = self.service.get_order(self.order_ids[row])
        OrderDetailsDialog(self.service, details, self).exec()
        self.refresh()
