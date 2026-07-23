"""Typed records for sales workflows."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class InvoiceSummary:
    id: int
    document_number: str
    document_type: str
    customer_name: str
    status: str
    issue_date: date
    total: Decimal
    paid_amount: Decimal
    credit_amount: Decimal
    balance: Decimal


@dataclass(frozen=True, slots=True)
class PaymentInput:
    invoice_id: int
    amount: Decimal
    payment_method: str
    reference: str = ""
    notes: str = ""
    is_advance: bool = False


@dataclass(frozen=True, slots=True)
class PaymentSummary:
    id: int
    payment_number: str
    invoice_number: str
    customer_name: str
    amount: Decimal
    payment_type: str
    payment_method: str
    received_on: date


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    occurred_at: datetime
    reference: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal
