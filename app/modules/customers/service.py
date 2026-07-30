"""Customer validation and use cases."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date
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
    from app.modules.cloud_storage import CloudStorageService
    from app.modules.customers.google_sheets import GoogleCustomerSheetSync

CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,29}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GST_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
PREFERRED_COURIERS = frozenset({"ST", "PROFESSIONAL", "DTDC", "BUS", "TRAIN", "OTHER TRANSPORT"})
CUSTOMER_STORAGE_FOLDERS = {
    "Design": "design",
    "Gangsheet": "gangsheet",
    "Invoice Copy": "invoice-copy",
    "Payment Receipt": "payment-receipt",
}


class CustomerValidationError(ValueError):
    pass


class CustomerNotFoundError(LookupError):
    pass


class DuplicateCustomerCodeError(ValueError):
    pass


class CustomerDeletionError(ValueError):
    pass


class CustomerStorageDateExistsError(ValueError):
    pass


class CustomerService:
    def __init__(
        self,
        repository: CustomerRepository,
        authentication_service: AuthenticationService | None = None,
        sheet_sync: GoogleCustomerSheetSync | None = None,
        storage_service: CloudStorageService | None = None,
    ) -> None:
        self._repository = repository
        self._authentication_service = authentication_service
        self._sheet_sync = sheet_sync
        self._storage_service = storage_service

    def set_storage_service(self, storage_service: CloudStorageService) -> None:
        self._storage_service = storage_service

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
        storage_prefix = self._storage_prefix(normalized)
        created = self._details(self._repository.create(normalized, storage_prefix=storage_prefix))
        created = self.ensure_customer_storage(created.summary.id)
        self.sync_customer_sheet()
        return created

    def update_customer(self, customer_id: int, data: CustomerInput) -> CustomerDetails:
        self._require("customers.manage")
        current = self._repository.get(customer_id)
        if current is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        delivery_type = data.delivery_type.strip().title()
        expected_prefix = "LC" if delivery_type == "Local" else "CR"
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
            sync_async = getattr(self._sheet_sync, "sync_async", None)
            if callable(sync_async):
                sync_async()
            else:
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

    def create_google_storage_catalog_entry(self, cloud_file) -> str:
        if self._sheet_sync is None or not self._sheet_sync.is_connected:
            return ""
        return self._sheet_sync.create_storage_catalog_entry(cloud_file)

    @property
    def google_drive_url(self) -> str | None:
        return getattr(self._sheet_sync, "root_folder_url", None)

    def ensure_customer_storage(self, customer_id: int) -> CustomerDetails:
        self._require("customers.view")
        customer = self._repository.get(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        storage_prefix = customer.storage_prefix or self._storage_prefix_from_customer(customer)
        drive_id = customer.google_drive_folder_id
        provision_drive = getattr(
            self._sheet_sync,
            "provision_customer_root_async",
            None,
        )
        if (
            self._sheet_sync is not None
            and self._sheet_sync.is_connected
            and callable(provision_drive)
        ):
            future = provision_drive(storage_prefix.removeprefix("customers/"))
            future.add_done_callback(
                lambda completed, customer_id=customer_id, prefix=storage_prefix: (
                    self._save_drive_folder_result(customer_id, prefix, completed)
                )
            )
        updated = self._repository.set_storage(
            customer_id,
            storage_prefix=storage_prefix,
            google_drive_folder_id=drive_id,
        )
        if updated is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        return self._details(updated)

    def _save_drive_folder_result(self, customer_id: int, storage_prefix: str, future) -> None:
        try:
            drive_id = future.result()
        except Exception:
            return
        self._repository.set_storage(
            customer_id,
            storage_prefix=storage_prefix,
            google_drive_folder_id=drive_id,
        )
        self.sync_customer_sheet()

    def customer_storage_dates(self, customer_id: int) -> list[str]:
        self.ensure_customer_storage(customer_id)
        return [
            item.folder_date.isoformat()
            for item in self._repository.list_storage_dates(customer_id)
        ]

    def create_customer_date_folder(
        self,
        customer_id: int,
        folder_date: date | None = None,
    ) -> str:
        self._require("customers.manage")
        details = self.ensure_customer_storage(customer_id)
        selected_date = folder_date or date.today()
        if any(
            item.folder_date == selected_date
            for item in self._repository.list_storage_dates(customer_id)
        ):
            raise CustomerStorageDateExistsError(
                f"A folder for {selected_date.strftime('%d-%m-%Y')} already exists."
            )
        record = self._repository.create_storage_date(customer_id, selected_date)
        if record is None:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}")
        date_name = selected_date.isoformat()
        if self._storage_service is not None:
            self._storage_service.ensure_folders_async(
                f"{details.storage_prefix}/{date_name}/{folder}"
                for folder in CUSTOMER_STORAGE_FOLDERS.values()
            )
        provision_drive = getattr(
            self._sheet_sync,
            "provision_customer_folders_async",
            None,
        )
        if (
            self._sheet_sync is not None
            and self._sheet_sync.is_connected
            and callable(provision_drive)
        ):
            future = provision_drive(
                details.storage_prefix.removeprefix("customers/"),
                date_name,
            )
            future.add_done_callback(
                lambda completed, customer_id=customer_id, selected_date=selected_date: (
                    self._save_date_drive_result(
                        customer_id,
                        selected_date,
                        completed,
                    )
                )
            )
        return date_name

    def _save_date_drive_result(self, customer_id: int, folder_date: date, future) -> None:
        try:
            drive_id = future.result()
        except Exception:
            return
        self._repository.set_storage_date_drive_id(
            customer_id,
            folder_date,
            drive_id,
        )

    def list_customer_files(self, customer_id: int, date_name: str, folder_name: str):
        self._require("customers.view")
        details = self.ensure_customer_storage(customer_id)
        folder = self._storage_folder(folder_name)
        if self._storage_service is None:
            return []
        return self._storage_service.list_prefix(f"{details.storage_prefix}/{date_name}/{folder}")

    def search_all_customer_files(self, query: str):
        self._require("customers.view")
        if self._storage_service is None:
            return []
        cleaned = query.strip().casefold()
        if not cleaned:
            return []
        variants = {cleaned, cleaned.replace("/", "-")}
        date_match = re.fullmatch(r"([0-9]{2})-([0-9]{2})-([0-9]{4})", cleaned)
        if date_match is not None:
            variants.add(
                f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"
            )
        return [
            item
            for item in self._storage_service.list_prefix("customers")
            if any(
                variant in item.original_name.casefold()
                or variant in item.object_key.casefold()
                for variant in variants
            )
        ]

    def search_all_customer_images(self, source: Path):
        self._require("customers.view")
        if self._storage_service is None:
            return []
        return self._storage_service.search_similar_images(source, "customers")

    def upload_customer_file(
        self,
        customer_id: int,
        date_name: str,
        folder_name: str,
        source: Path,
    ):
        self._require("customers.manage")
        details = self.ensure_customer_storage(customer_id)
        if date_name not in self.customer_storage_dates(customer_id):
            raise CustomerValidationError("Create this date folder before uploading files")
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        folder = self._storage_folder(folder_name)
        prefix = f"{details.storage_prefix}/{date_name}/{folder}"
        original_name = None
        if folder_name == "Design":
            original_name = self._next_design_filename(
                details.summary.code,
                details.storage_prefix,
                source.name,
            )
        record = self._storage_service.queue_upload(
            source,
            prefix,
            auto_sync=False,
            original_name=original_name,
        )
        self._storage_service.synchronize_async()
        return record

    def customer_file_url(self, cloud_file_id: int) -> str:
        self._require("customers.view")
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        return self._storage_service.access_url(cloud_file_id)

    def download_customer_file(self, cloud_file_id: int, destination: Path) -> Path:
        self._require("customers.view")
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        return self._storage_service.download(cloud_file_id, destination)

    def replace_customer_file(self, cloud_file_id: int, source: Path):
        """Replace a managed customer file while retaining its ID and folder path."""

        self._require("customers.manage")
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        return self._storage_service.replace(cloud_file_id, source)

    def copy_customer_file(
        self,
        cloud_file_id: int,
        customer_id: int,
        date_name: str,
        folder_name: str,
    ):
        self._require("customers.manage")
        details = self.ensure_customer_storage(customer_id)
        if date_name not in self.customer_storage_dates(customer_id):
            raise CustomerValidationError("Create this date folder before pasting files")
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        folder = self._storage_folder(folder_name)
        prefix = f"{details.storage_prefix}/{date_name}/{folder}"
        original_name = None
        if folder_name == "Design":
            source_record = self._storage_service.get(cloud_file_id)
            source_name = re.sub(
                r"^[A-Z0-9-]+ - DE[0-9]+ - ",
                "",
                source_record.original_name,
                count=1,
                flags=re.IGNORECASE,
            )
            original_name = self._next_design_filename(
                details.summary.code,
                details.storage_prefix,
                source_name,
            )
        return self._storage_service.copy(
            cloud_file_id,
            prefix,
            original_name=original_name,
        )

    def delete_customer_file(self, cloud_file_id: int) -> None:
        self._require("customers.manage")
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        self._storage_service.delete(cloud_file_id)

    def _next_design_filename(
        self,
        customer_code: str,
        customer_storage_prefix: str,
        source_name: str,
    ) -> str:
        if self._storage_service is None:
            raise RuntimeError("File storage is unavailable")
        pattern = re.compile(
            rf"^{re.escape(customer_code)} - DE([0-9]+) - ",
            re.IGNORECASE,
        )
        used_numbers = [
            int(match.group(1))
            for item in self._storage_service.list_prefix(customer_storage_prefix)
            if (match := pattern.match(item.original_name)) is not None
        ]
        design_number = max(used_numbers, default=0) + 1
        return f"{customer_code} - DE{design_number} - {source_name}"

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
    def _storage_folder(folder_name: str) -> str:
        try:
            return CUSTOMER_STORAGE_FOLDERS[folder_name]
        except KeyError as error:
            raise CustomerValidationError("Invalid customer storage folder") from error

    @staticmethod
    def _storage_prefix(data: CustomerInput) -> str:
        district = data.billing_address.district or "DISTRICT"
        business = data.business_name or data.name or "CUSTOMER"
        folder = f"{data.code} - {business} - {district}".upper()
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", folder)
        safe = re.sub(r"\s+", " ", safe).strip(" .-")
        return f"customers/{safe}"

    @staticmethod
    def _storage_prefix_from_customer(customer: Customer) -> str:
        addresses = {address.address_type: address for address in customer.addresses}
        billing = addresses.get("billing")
        data = CustomerInput(
            code=customer.code,
            name=customer.name,
            phone=customer.phone,
            business_name=customer.business_name,
            billing_address=AddressInput(district=billing.district if billing is not None else ""),
        )
        return CustomerService._storage_prefix(data)

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
            (address for address in customer.addresses if address.address_type == "billing"),
            None,
        )
        business = (customer.business_name or customer.name or "CUSTOMER").strip().upper()
        district = (
            (
                billing_address.district
                if billing_address is not None and billing_address.district
                else "DISTRICT"
            )
            .strip()
            .upper()
        )
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
            storage_prefix=customer.storage_prefix,
            google_drive_folder_id=customer.google_drive_folder_id,
        )
