"""Customer validation and use cases."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path, PurePosixPath

from app.modules.authentication import AuthenticationService
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    AddressInput,
    CustomerDetails,
    CustomerInput,
    CustomerSummary,
)

CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,29}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GST_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
PREFERRED_COURIERS = frozenset(
    {"ST", "PROFESSIONAL", "DTDC", "BUS", "TRAIN", "OTHER TRANSPORT"}
)


class CustomerValidationError(ValueError):
    pass


class CustomerNotFoundError(LookupError):
    pass


class DuplicateCustomerCodeError(ValueError):
    pass


class CustomerService:
    def __init__(
        self,
        repository: CustomerRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self._repository = repository
        self._authentication_service = authentication_service

    def list_customers(
        self, query: str = "", *, active: bool | None = True
    ) -> list[CustomerSummary]:
        self._require("customers.view")
        return [
            self._summary(customer) for customer in self._repository.search(query, active=active)
        ]

    def get_customer(self, customer_id: int) -> CustomerDetails:
        self._require("customers.view")
        customer = self._repository.get(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        return self._details(customer)

    def create_customer(self, data: CustomerInput) -> CustomerDetails:
        self._require("customers.manage")
        if not data.code.strip():
            delivery_type = data.delivery_type.strip().title()
            data = replace(data, code=self._repository.next_code(delivery_type))
        normalized = self._validate(data)
        if self._repository.get_by_code(normalized.code) is not None:
            raise DuplicateCustomerCodeError(f"Customer code already exists: {normalized.code}")
        return self._details(self._repository.create(normalized))

    def update_customer(self, customer_id: int, data: CustomerInput) -> CustomerDetails:
        self._require("customers.manage")
        current = self._repository.get(customer_id)
        if current is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        delivery_type = data.delivery_type.strip().title()
        expected_prefix = "LO" if delivery_type == "Local" else "CO"
        if not data.code.startswith(expected_prefix):
            data = replace(data, code=self._repository.next_code(delivery_type))
        normalized = self._validate(data)
        existing = self._repository.get_by_code(normalized.code)
        if existing is not None and existing.id != customer_id:
            raise DuplicateCustomerCodeError(f"Customer code already exists: {normalized.code}")
        customer = self._repository.update(customer_id, normalized)
        if customer is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        return self._details(customer)

    def deactivate_customer(self, customer_id: int) -> None:
        self._require("customers.manage")
        if not self._repository.deactivate(customer_id):
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")

    def add_file_reference(self, customer_id: int, label: str, stored_path: str) -> None:
        self._require("customers.manage")
        path = PurePosixPath(stored_path)
        if not label.strip() or Path(stored_path).is_absolute() or ".." in path.parts:
            raise CustomerValidationError("File reference must use a managed relative path")
        if (
            self._repository.add_file_reference(
                customer_id, label=label.strip(), stored_path=path.as_posix()
            )
            is None
        ):
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")

    def _require(self, permission: str) -> None:
        if self._authentication_service is not None:
            self._authentication_service.require_permission(permission)

    @staticmethod
    def _validate(data: CustomerInput) -> CustomerInput:
        code = data.code.strip().upper()
        name = data.name.strip()
        phone = CustomerService._phone(data.phone, required=True)
        whatsapp = CustomerService._phone(data.whatsapp_number, required=False)
        email = data.email.strip().casefold() if data.email else None
        gst = data.gst_number.strip().upper()
        delivery_type = data.delivery_type.strip().title()
        preferred_courier = data.preferred_courier.strip().upper()
        other_transport_name = data.other_transport_name.strip()
        if not CODE_PATTERN.fullmatch(code):
            raise CustomerValidationError("Customer code must be 2-30 letters, numbers, or hyphens")
        if not name:
            raise CustomerValidationError("Customer name is required")
        if email and not EMAIL_PATTERN.fullmatch(email):
            raise CustomerValidationError("Email address is invalid")
        if gst and not GST_PATTERN.fullmatch(gst):
            raise CustomerValidationError("GST number is invalid")
        if delivery_type not in {"Courier", "Local"}:
            raise CustomerValidationError("Delivery type must be Courier or Local")
        if delivery_type == "Local":
            preferred_courier = ""
            other_transport_name = ""
        elif preferred_courier not in PREFERRED_COURIERS:
            raise CustomerValidationError("Select a valid preferred courier")
        if preferred_courier == "OTHER TRANSPORT" and not other_transport_name:
            raise CustomerValidationError("Enter the other transport name")
        if preferred_courier != "OTHER TRANSPORT":
            other_transport_name = ""
        return CustomerInput(
            name=name,
            phone=phone,
            code=code,
            business_name=data.business_name.strip(),
            whatsapp_number=whatsapp,
            delivery_type=delivery_type,
            preferred_courier=preferred_courier,
            other_transport_name=other_transport_name,
            email=email,
            gst_number=gst,
            billing_address=CustomerService._address(data.billing_address),
            shipping_address=CustomerService._address(data.shipping_address),
            notes=data.notes.strip(),
        )

    @staticmethod
    def _phone(value: str, *, required: bool) -> str:
        cleaned = re.sub(r"[\s()\-]", "", value)
        if not cleaned and not required:
            return ""
        if not re.fullmatch(r"\+?[0-9]{7,15}", cleaned):
            raise CustomerValidationError("Phone number must contain 7-15 digits")
        return cleaned

    @staticmethod
    def _address(address: AddressInput) -> AddressInput:
        return AddressInput(
            line1=address.line1.strip(),
            line2=address.line2.strip(),
            city=address.city.strip(),
            state=address.state.strip(),
            postal_code=address.postal_code.strip(),
            country=address.country.strip() or "India",
        )

    @staticmethod
    def _summary(customer: Customer) -> CustomerSummary:
        return CustomerSummary(
            id=customer.id,
            code=customer.code,
            name=customer.name,
            business_name=customer.business_name,
            phone=customer.phone,
            whatsapp_number=customer.whatsapp_number,
            delivery_type=customer.delivery_type,
            preferred_courier=customer.preferred_courier,
            other_transport_name=customer.other_transport_name,
            email=customer.email,
            is_active=customer.is_active,
        )

    @staticmethod
    def _details(customer: Customer) -> CustomerDetails:
        addresses = {address.address_type: address for address in customer.addresses}

        def address(kind: str) -> AddressInput:
            value = addresses.get(kind)
            return (
                AddressInput()
                if value is None
                else AddressInput(
                    value.line1,
                    value.line2,
                    value.city,
                    value.state,
                    value.postal_code,
                    value.country,
                )
            )

        return CustomerDetails(
            summary=CustomerService._summary(customer),
            whatsapp_number=customer.whatsapp_number,
            gst_number=customer.gst_number,
            billing_address=address("billing"),
            shipping_address=address("shipping"),
            notes=customer.notes,
            file_references=tuple(
                (reference.label, reference.stored_path) for reference in customer.file_references
            ),
        )
