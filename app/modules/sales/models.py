"""Sales, invoice, payment, and credit-note persistence."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.authentication.models import utc_now


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    document_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    converted_from_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    customer = relationship("Customer")
    order = relationship("Order")
    items: Mapped[list[InvoiceItem]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="invoice", lazy="selectin")
    credit_notes: Mapped[list[CreditNote]] = relationship(back_populates="invoice", lazy="selectin")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    invoice: Mapped[Invoice] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_type: Mapped[str] = mapped_column(String(20))
    payment_method: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str] = mapped_column(String(100), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    received_on: Mapped[date] = mapped_column(Date)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class CreditNote(Base):
    __tablename__ = "credit_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    credit_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reason: Mapped[str] = mapped_column(Text)
    issued_on: Mapped[date] = mapped_column(Date)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    invoice: Mapped[Invoice] = relationship(back_populates="credit_notes")
