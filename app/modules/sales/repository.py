"""Transactional sales persistence and ledgers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.inventory.models import Purchase, Supplier
from app.modules.orders.models import Order
from app.modules.sales.models import CreditNote, Invoice, InvoiceItem, Payment


class SalesRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def next_sequence(self, prefix: str, model, column) -> int:
        with session_scope(self.factory) as session:
            values = session.scalars(select(column).where(column.like(f"{prefix}%")))
            sequences = [
                int(value.removeprefix(prefix))
                for value in values
                if value.removeprefix(prefix).isdigit()
            ]
            return max(sequences, default=0) + 1

    def create_from_order(
        self,
        order_id: int,
        number: str,
        document_type: str,
        user_id: int | None,
        converted_from_id: int | None = None,
    ) -> Invoice:
        with session_scope(self.factory) as session:
            order = session.scalar(
                select(Order).where(Order.id == order_id).options(selectinload(Order.items))
            )
            if order is None:
                raise LookupError("Order not found")
            document = Invoice(
                document_number=number,
                document_type=document_type,
                status="Open" if document_type == "Invoice" else "Quoted",
                customer_id=order.customer_id,
                order_id=order.id,
                converted_from_id=converted_from_id,
                issue_date=date.today(),
                due_date=order.due_date,
                subtotal=order.subtotal,
                discount=order.discount,
                tax=order.tax,
                total=order.total,
                paid_amount=Decimal("0"),
                credit_amount=Decimal("0"),
                balance=order.total,
                notes=order.notes,
                created_by_user_id=user_id,
            )
            document.items.extend(
                InvoiceItem(
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    discount=item.discount,
                    tax=item.tax,
                    total=item.total,
                )
                for item in order.items
            )
            session.add(document)
            session.flush()
            document_id = document.id
        return self.get(document_id)

    def convert_quotation(self, quotation_id: int, number: str, user_id: int | None) -> Invoice:
        quotation = self.get(quotation_id)
        if quotation.document_type != "Quotation":
            raise ValueError("Only a quotation can be converted")
        if quotation.status == "Converted":
            raise ValueError("Quotation is already converted")
        if quotation.order_id is None:
            raise ValueError("Quotation is not linked to an order")
        invoice = self.create_from_order(
            quotation.order_id,
            number,
            "Invoice",
            user_id,
            quotation.id,
        )
        with session_scope(self.factory) as session:
            stored = session.get(Invoice, quotation_id)
            if stored is None:
                raise LookupError("Quotation not found")
            stored.status = "Converted"
        return invoice

    def get(self, document_id: int) -> Invoice:
        with session_scope(self.factory) as session:
            document = session.scalar(
                select(Invoice)
                .where(Invoice.id == document_id)
                .options(
                    selectinload(Invoice.customer),
                    selectinload(Invoice.items),
                    selectinload(Invoice.payments),
                    selectinload(Invoice.credit_notes),
                )
            )
            if document is None:
                raise LookupError("Sales document not found")
            return document

    def list_documents(self, document_type: str | None = None) -> list[Invoice]:
        with session_scope(self.factory) as session:
            statement = select(Invoice).options(selectinload(Invoice.customer))
            if document_type:
                statement = statement.where(Invoice.document_type == document_type)
            return list(session.scalars(statement.order_by(Invoice.created_at.desc())))

    def record_payment(
        self,
        invoice_id: int,
        number: str,
        amount: Decimal,
        payment_type: str,
        method: str,
        reference: str,
        notes: str,
        user_id: int | None,
    ) -> Invoice:
        """Create an immutable payment and update its invoice in one transaction."""
        with session_scope(self.factory) as session:
            invoice = session.get(Invoice, invoice_id)
            if invoice is None or invoice.document_type != "Invoice":
                raise LookupError("Invoice not found")
            if amount <= 0 or amount > invoice.balance:
                raise ValueError("Payment must be positive and cannot exceed balance")
            invoice.paid_amount += amount
            invoice.balance -= amount
            invoice.status = "Paid" if invoice.balance == 0 else "Part Paid"
            session.add(
                Payment(
                    payment_number=number,
                    invoice_id=invoice.id,
                    amount=amount,
                    payment_type=payment_type,
                    payment_method=method,
                    reference=reference,
                    notes=notes,
                    received_on=date.today(),
                    created_by_user_id=user_id,
                )
            )
        return self.get(invoice_id)

    def issue_credit(
        self,
        invoice_id: int,
        number: str,
        amount: Decimal,
        reason: str,
        user_id: int | None,
    ) -> Invoice:
        with session_scope(self.factory) as session:
            invoice = session.get(Invoice, invoice_id)
            if invoice is None or invoice.document_type != "Invoice":
                raise LookupError("Invoice not found")
            if amount <= 0 or amount > invoice.balance:
                raise ValueError("Credit must be positive and cannot exceed balance")
            invoice.credit_amount += amount
            invoice.balance -= amount
            invoice.status = "Paid" if invoice.balance == 0 else "Part Paid"
            session.add(
                CreditNote(
                    credit_number=number,
                    invoice_id=invoice.id,
                    amount=amount,
                    reason=reason,
                    issued_on=date.today(),
                    created_by_user_id=user_id,
                )
            )
        return self.get(invoice_id)

    def list_payments(self) -> list[Payment]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    select(Payment)
                    .options(selectinload(Payment.invoice).selectinload(Invoice.customer))
                    .order_by(Payment.created_at.desc())
                )
            )

    def customer_documents(self, customer_id: int) -> list[Invoice]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    select(Invoice)
                    .where(
                        Invoice.customer_id == customer_id,
                        Invoice.document_type == "Invoice",
                    )
                    .options(
                        selectinload(Invoice.payments),
                        selectinload(Invoice.credit_notes),
                    )
                    .order_by(Invoice.created_at)
                )
            )

    def supplier_purchases(self, supplier_id: int) -> tuple[Supplier, list[Purchase]]:
        with session_scope(self.factory) as session:
            supplier = session.get(Supplier, supplier_id)
            if supplier is None:
                raise LookupError("Supplier not found")
            purchases = list(
                session.scalars(
                    select(Purchase)
                    .where(Purchase.supplier_id == supplier_id)
                    .order_by(Purchase.order_date)
                )
            )
            session.expunge(supplier)
            return supplier, purchases
