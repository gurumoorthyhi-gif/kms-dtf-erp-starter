"""Quotation, invoice, and payment workspace pages."""

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
from app.modules.sales import PaymentInput, SalesService


class SalesPage(QWidget):
    def __init__(
        self, service: SalesService, orders: OrderService, *, auto_refresh: bool = True
    ) -> None:
        super().__init__()
        self.service, self.orders = service, orders
        self.quotation_ids: list[int] = []
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.order = QComboBox()
        create = QPushButton("Create quotation")
        convert = QPushButton("Convert to invoice")
        toolbar.addWidget(self.order, 1)
        toolbar.addWidget(create)
        toolbar.addWidget(convert)
        layout.addLayout(toolbar)
        self.table = _document_table()
        layout.addWidget(self.table)
        create.clicked.connect(self.create_quotation)
        convert.clicked.connect(self.convert)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        self.order.clear()
        for order in self.orders.list_orders():
            self.order.addItem(f"{order.order_number} · {order.customer_name}", order.id)
        documents = self.service.list_documents("Quotation")
        self.quotation_ids = [item.id for item in documents]
        _fill_documents(self.table, documents)

    def create_quotation(self) -> None:
        if self.order.currentData() is not None:
            self.service.create_quotation(int(self.order.currentData()))
            self.refresh()

    def convert(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.quotation_ids):
            try:
                self.service.convert_to_invoice(self.quotation_ids[row])
            except ValueError as error:
                QMessageBox.warning(self, "Conversion failed", str(error))
            self.refresh()


class InvoicesPage(QWidget):
    def __init__(
        self, service: SalesService, orders: OrderService, *, auto_refresh: bool = True
    ) -> None:
        super().__init__()
        self.service, self.orders = service, orders
        self.invoice_ids: list[int] = []
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.order = QComboBox()
        generate = QPushButton("Generate invoice")
        export = QPushButton("Export PDF")
        toolbar.addWidget(self.order, 1)
        toolbar.addWidget(generate)
        toolbar.addWidget(export)
        layout.addLayout(toolbar)
        self.table = _document_table()
        layout.addWidget(self.table)
        generate.clicked.connect(self.generate)
        export.clicked.connect(self.export)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        self.order.clear()
        for order in self.orders.list_orders():
            self.order.addItem(f"{order.order_number} · {order.customer_name}", order.id)
        documents = self.service.list_documents("Invoice")
        self.invoice_ids = [item.id for item in documents]
        _fill_documents(self.table, documents)

    def generate(self) -> None:
        if self.order.currentData() is not None:
            self.service.generate_invoice(int(self.order.currentData()))
            self.refresh()

    def export(self) -> None:
        row = self.table.currentRow()
        if not 0 <= row < len(self.invoice_ids):
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export invoice", "invoice.pdf", "PDF (*.pdf)"
        )
        if filename:
            self.service.export_pdf(self.invoice_ids[row], Path(filename))


class PaymentsPage(QWidget):
    def __init__(self, service: SalesService, *, auto_refresh: bool = True) -> None:
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        self.invoice = QComboBox()
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("Amount")
        self.method = QComboBox()
        self.method.addItems(("Cash", "UPI", "Bank transfer", "Card"))
        self.reference = QLineEdit()
        self.reference.setPlaceholderText("Reference")
        self.advance = QCheckBox("Advance")
        record = QPushButton("Record payment")
        credit = QPushButton("Issue credit note")
        for widget in (
            self.invoice,
            self.amount,
            self.method,
            self.reference,
            self.advance,
            record,
            credit,
        ):
            form.addWidget(widget)
        layout.addLayout(form)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Payment", "Invoice", "Customer", "Type", "Method", "Date", "Amount"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        record.clicked.connect(self.record)
        credit.clicked.connect(self.credit)
        if auto_refresh:
            self.refresh()

    def refresh(self) -> None:
        self.invoice.clear()
        for invoice in self.service.list_documents("Invoice"):
            if invoice.balance > 0:
                self.invoice.addItem(
                    f"{invoice.document_number} · Balance {invoice.balance}", invoice.id
                )
        payments = self.service.list_payments()
        self.table.setRowCount(len(payments))
        for row, payment in enumerate(payments):
            values = (
                payment.payment_number,
                payment.invoice_number,
                payment.customer_name,
                payment.payment_type,
                payment.payment_method,
                payment.received_on.isoformat(),
                str(payment.amount),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def record(self) -> None:
        if self.invoice.currentData() is None:
            return
        try:
            self.service.record_payment(
                PaymentInput(
                    int(self.invoice.currentData()),
                    Decimal(self.amount.text()),
                    self.method.currentText(),
                    self.reference.text(),
                    is_advance=self.advance.isChecked(),
                )
            )
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, "Payment failed", str(error))
        self.refresh()

    def credit(self) -> None:
        if self.invoice.currentData() is None:
            return
        try:
            self.service.issue_credit_note(
                int(self.invoice.currentData()),
                Decimal(self.amount.text()),
                self.reference.text(),
            )
        except (ValueError, InvalidOperation) as error:
            QMessageBox.warning(self, "Credit note failed", str(error))
        self.refresh()


def _document_table() -> QTableWidget:
    table = QTableWidget(0, 7)
    table.setHorizontalHeaderLabels(
        ["Number", "Customer", "Status", "Date", "Total", "Paid/Credit", "Balance"]
    )
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    return table


def _fill_documents(table: QTableWidget, documents) -> None:
    table.setRowCount(len(documents))
    for row, item in enumerate(documents):
        values = (
            item.document_number,
            item.customer_name,
            item.status,
            item.issue_date.isoformat(),
            str(item.total),
            str(item.paid_amount + item.credit_amount),
            str(item.balance),
        )
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))
