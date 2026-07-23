"""Typed customer inputs and service outputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AddressInput:
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "India"


@dataclass(frozen=True, slots=True)
class CustomerInput:
    code: str
    name: str
    phone: str
    business_name: str = ""
    whatsapp_number: str = ""
    email: str | None = None
    gst_number: str = ""
    billing_address: AddressInput = AddressInput()
    shipping_address: AddressInput = AddressInput()
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CustomerSummary:
    id: int
    code: str
    name: str
    business_name: str
    phone: str
    email: str | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class CustomerDetails:
    summary: CustomerSummary
    whatsapp_number: str
    gst_number: str
    billing_address: AddressInput
    shipping_address: AddressInput
    notes: str
    file_references: tuple[tuple[str, str], ...]
