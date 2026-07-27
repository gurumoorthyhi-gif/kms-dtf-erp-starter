"""Customer validation and use cases."""

from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from app.modules.authentication import AuthenticationService
from app.modules.customers.google_sheets import CustomerSyncError
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    AddressInput,
    CustomerDetails,
    CustomerInput,
    CustomerSummary,
)

if TYPE_CHECKING:
    from app.modules.customers.google_sheets import GoogleCustomerSheetSync

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


class CustomerDeletionError(ValueError):
    pass


class CustomerService:
    def __init__(
        self,
        repository: CustomerRepository,
        authentication_service: AuthenticationService | None = None,
        sheet_sync: GoogleCustomerSheetSync | None = None,
    ) -> None:
        self._repository = repository
        self._authentication_service = authentication_service
        self._sheet_sync = sheet_sync

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
        created = self._details(self._repository.create(normalized))
        self.sync_customer_sheet()
        return created

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
        details = self._details(customer)
        self.sync_customer_sheet()
        return details

    def deactivate_customer(self, customer_id: int) -> None:
        self._require("customers.manage")
        if not self._repository.deactivate(customer_id):
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        self.sync_customer_sheet()

    def delete_customer(self, customer_id: int) -> None:
        self._require("customers.manage")
        try:
            deleted = self._repository.delete(customer_id)
        except IntegrityError as error:
            raise CustomerDeletionError(
                "This customer has linked transactions and cannot be deleted. "
                "Use Deactivate instead."
            ) from error
        if not deleted:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        self.sync_customer_sheet()

    def sync_customer_sheet(self) -> None:
        if self._sheet_sync is not None:
            self._sheet_sync.sync()

    @property
    def google_drive_available(self) -> bool:
        return self._sheet_sync is not None

    @property
    def google_drive_connected(self) -> bool:
        return self._sheet_sync is not None and self._sheet_sync.is_connected

    @property
    def customer_sheet_url(self) -> str | None:
        return self._sheet_sync.spreadsheet_url if self._sheet_sync is not None else None

    def connect_google_drive(self) -> str:
        if self._sheet_sync is None:
            raise CustomerSyncError("Google Drive integration is not available in this build.")
        return self._sheet_sync.connect()

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
        try:
            preferred_rate = Decimal(str(data.preferred_rate)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as error:
            raise CustomerValidationError("Preferred rate must be a valid amount") from error
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
        if preferred_rate < 0:
            raise CustomerValidationError("Preferred rate cannot be negative")
        return CustomerInput(
            name=name,
            phone=phone,
            code=code,
            business_name=data.business_name.strip(),
            whatsapp_number=whatsapp,
            delivery_type=delivery_type,
            preferred_courier=preferred_courier,
            other_transport_name=other_transport_name,
            preferred_rate=preferred_rate,
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
            landmark=address.landmark.strip(),
            district=address.district.strip(),
            state=address.state.strip(),
            postal_code=address.postal_code.strip(),
            country=address.country.strip() or "India",
        )

    @staticmethod
    def _summary(customer: Customer) -> CustomerSummary:
        billing_address = next(
            (
                address
                for address in customer.addresses
                if address.address_type == "billing"
            ),
            None,
        )
        business = (customer.business_name or customer.name or "CUSTOMER").strip().upper()
        district = (
            billing_address.district
            if billing_address is not None and billing_address.district
            else "DISTRICT"
        ).strip().upper()
        return CustomerSummary(
            id=customer.id,
            code=customer.code,
            display_identifier=f"{customer.code} - {business} - {district}",
            name=customer.name,
            business_name=customer.business_name,
            phone=customer.phone,
            whatsapp_number=customer.whatsapp_number,
            delivery_type=customer.delivery_type,
            preferred_courier=customer.preferred_courier,
            other_transport_name=customer.other_transport_name,
            preferred_rate=customer.preferred_rate,
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
                    line1=value.line1,
                    line2=value.line2,
                    city=value.city,
                    landmark=value.landmark,
                    district=value.district,
                    state=value.state,
                    postal_code=value.postal_code,
                    country=value.country,
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
