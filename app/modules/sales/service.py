"""Sales documents, payments, credits, PDF export, and ledgers."""

from datetime import datetime, time
from decimal import Decimal
from html import escape
from pathlib import Path

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter

from app.modules.authentication import AuthenticationService
from app.modules.sales.models import CreditNote, Invoice, Payment
from app.modules.sales.repository import SalesRepository
from app.modules.sales.schemas import (
    InvoiceSummary,
    LedgerEntry,
    PaymentInput,
    PaymentSummary,
)


class SalesService:
    def __init__(
        self,
        repository: SalesRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create_quotation(self, order_id: int) -> InvoiceSummary:
        self._require("sales.manage")
        return self._summary(
            self.repository.create_from_order(
                order_id,
                self._number("QUO", Invoice, Invoice.document_number),
                "Quotation",
                self._user_id(),
            )
        )

    def generate_invoice(self, order_id: int) -> InvoiceSummary:
        self._require("sales.manage")
        return self._summary(
            self.repository.create_from_order(
                order_id,
                self._number("INV", Invoice, Invoice.document_number),
                "Invoice",
                self._user_id(),
            )
        )

    def convert_to_invoice(self, quotation_id: int) -> InvoiceSummary:
        self._require("sales.manage")
        return self._summary(
            self.repository.convert_quotation(
                quotation_id,
                self._number("INV", Invoice, Invoice.document_number),
                self._user_id(),
            )
        )

    def list_documents(self, document_type: str | None = None) -> list[InvoiceSummary]:
        self._require("sales.view")
        return [self._summary(item) for item in self.repository.list_documents(document_type)]

    def record_payment(self, data: PaymentInput) -> InvoiceSummary:
        self._require("payments.manage")
        if not data.payment_method.strip():
            raise ValueError("Payment method is required")
        invoice = self.repository.record_payment(
            data.invoice_id,
            self._number("PAY", Payment, Payment.payment_number),
            data.amount,
            "Advance" if data.is_advance else "Payment",
            data.payment_method.strip(),
            data.reference.strip(),
            data.notes.strip(),
            self._user_id(),
        )
        return self._summary(invoice)

    def issue_credit_note(self, invoice_id: int, amount: Decimal, reason: str) -> InvoiceSummary:
        self._require("payments.manage")
        if not reason.strip():
            raise ValueError("Credit-note reason is required")
        return self._summary(
            self.repository.issue_credit(
                invoice_id,
                self._number("CRN", CreditNote, CreditNote.credit_number),
                amount,
                reason.strip(),
                self._user_id(),
            )
        )

    def list_payments(self) -> list[PaymentSummary]:
        self._require("payments.view")
        return [
            PaymentSummary(
                item.id,
                item.payment_number,
                item.invoice.document_number,
                item.invoice.customer.name,
                item.amount,
                item.payment_type,
                item.payment_method,
                item.received_on,
            )
            for item in self.repository.list_payments()
        ]

    def customer_ledger(self, customer_id: int) -> list[LedgerEntry]:
        self._require("sales.view")
        raw: list[tuple[datetime, str, str, Decimal, Decimal]] = []
        for invoice in self.repository.customer_documents(customer_id):
            raw.append(
                (
                    invoice.created_at,
                    invoice.document_number,
                    "Invoice",
                    invoice.total,
                    Decimal("0"),
                )
            )
            raw.extend(
                (
                    payment.created_at,
                    payment.payment_number,
                    payment.payment_type,
                    Decimal("0"),
                    payment.amount,
                )
                for payment in invoice.payments
            )
            raw.extend(
                (
                    credit.created_at,
                    credit.credit_number,
                    "Credit note",
                    Decimal("0"),
                    credit.amount,
                )
                for credit in invoice.credit_notes
            )
        return self._ledger(raw)

    def supplier_ledger(self, supplier_id: int) -> list[LedgerEntry]:
        self._require("purchases.view")
        _, purchases = self.repository.supplier_purchases(supplier_id)
        raw = [
            (
                datetime.combine(purchase.order_date, time.min),
                purchase.purchase_number,
                "Purchase",
                Decimal("0"),
                purchase.total,
            )
            for purchase in purchases
        ]
        return self._ledger(raw)

    def export_pdf(self, invoice_id: int, destination: Path) -> Path:
        self._require("sales.view")
        invoice = self.repository.get(invoice_id)
        destination = destination.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = "".join(
            f"<tr><td>{escape(item.description)}</td><td>{item.quantity}</td>"
            f"<td>{item.unit_price}</td><td>{item.total}</td></tr>"
            for item in invoice.items
        )
        document = QTextDocument()
        document.setHtml(
            f"<h1>{escape(invoice.document_type)} {escape(invoice.document_number)}</h1>"
            f"<p>Customer: {escape(invoice.customer.name)}<br>Date: {invoice.issue_date}</p>"
            "<table width='100%' border='1' cellspacing='0' cellpadding='6'>"
            "<tr><th>Description</th><th>Qty</th><th>Rate</th><th>Total</th></tr>"
            f"{rows}</table><h2>Total: {invoice.total}</h2>"
            f"<p>Paid/Credited: {invoice.paid_amount + invoice.credit_amount}<br>"
            f"Balance: {invoice.balance}</p>"
        )
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(destination))
        document.print_(printer)
        return destination

    def _number(self, prefix: str, model, column) -> str:
        day = datetime.now().date()
        base = f"{prefix}-{day:%Y%m%d}-"
        return f"{base}{self.repository.next_sequence(base, model, column):04d}"

    @staticmethod
    def _summary(item: Invoice) -> InvoiceSummary:
        return InvoiceSummary(
            item.id,
            item.document_number,
            item.document_type,
            item.customer.name,
            item.status,
            item.issue_date,
            item.total,
            item.paid_amount,
            item.credit_amount,
            item.balance,
        )

    @staticmethod
    def _ledger(raw: list[tuple[datetime, str, str, Decimal, Decimal]]) -> list[LedgerEntry]:
        balance = Decimal("0")
        result = []
        for occurred_at, reference, description, debit, credit in sorted(raw):
            balance += debit - credit
            result.append(LedgerEntry(occurred_at, reference, description, debit, credit, balance))
        return result

    def _require(self, permission: str) -> None:
        if self.authentication_service:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if not self.authentication_service:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None
