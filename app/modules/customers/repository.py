"""Customer persistence operations."""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.customers.models import (
    Customer,
    CustomerAddress,
    CustomerFileReference,
    CustomerStorageDate,
)
from app.modules.customers.schemas import AddressInput, CustomerInput


class CustomerRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _load_options():
        return (
            selectinload(Customer.addresses),
            selectinload(Customer.file_references),
            selectinload(Customer.storage_dates),
        )

    def get(self, customer_id: int) -> Customer | None:
        with session_scope(self._session_factory) as session:
            statement = (
                select(Customer).where(Customer.id == customer_id).options(*self._load_options())
            )
            return session.scalar(statement)

    def get_by_code(self, code: str) -> Customer | None:
        with session_scope(self._session_factory) as session:
            return session.scalar(select(Customer).where(Customer.code == code))

    def next_code(self, delivery_type: str) -> str:
        """Return the next shared four-digit customer sequence with a type prefix."""

        prefix = "LC" if delivery_type == "Local" else "CR"
        with session_scope(self._session_factory) as session:
            codes = session.scalars(
                select(Customer.code).where(
                    Customer.code.like("LC____")
                    | Customer.code.like("CR____")
                    | Customer.code.like("LO____")
                    | Customer.code.like("CO____")
                )
            )
            serials = [int(code[-4:]) for code in codes if len(code) == 6 and code[-4:].isdigit()]
        serial = max(serials, default=0) + 1
        if serial > 9999:
            raise ValueError("Customer serial number limit has been reached")
        return f"{prefix}{serial:04d}"

    def search(
        self,
        query: str = "",
        *,
        active: bool | None = True,
    ) -> list[Customer]:
        with session_scope(self._session_factory) as session:
            statement = select(Customer).options(*self._load_options())
            if query:
                pattern = f"%{query}%"
                statement = statement.where(
                    or_(
                        Customer.code.ilike(pattern),
                        Customer.name.ilike(pattern),
                        Customer.business_name.ilike(pattern),
                        Customer.phone.ilike(pattern),
                    )
                )
            if active is not None:
                statement = statement.where(Customer.is_active.is_(active))
            return list(session.scalars(statement.order_by(Customer.id)))

    def create(self, data: CustomerInput, *, storage_prefix: str = "") -> Customer:
        with session_scope(self._session_factory) as session:
            customer = Customer(
                code=data.code,
                name=data.name,
                business_name=data.business_name,
                phone=data.phone,
                whatsapp_number=data.whatsapp_number,
                delivery_type=data.delivery_type,
                preferred_courier=data.preferred_courier,
                other_transport_name=data.other_transport_name,
                preferred_rate=data.preferred_rate,
                email=data.email,
                gst_number=data.gst_number,
                notes=data.notes,
                storage_prefix=storage_prefix,
                addresses=self._build_addresses(data),
            )
            session.add(customer)
            session.flush()
            customer_id = customer.id
        created = self.get(customer_id)
        if created is None:
            raise RuntimeError("Created customer could not be reloaded")
        return created

    def update(self, customer_id: int, data: CustomerInput) -> Customer | None:
        with session_scope(self._session_factory) as session:
            customer = session.scalar(
                select(Customer)
                .where(Customer.id == customer_id)
                .options(selectinload(Customer.addresses))
            )
            if customer is None:
                return None
            customer.code = data.code
            customer.name = data.name
            customer.business_name = data.business_name
            customer.phone = data.phone
            customer.whatsapp_number = data.whatsapp_number
            customer.delivery_type = data.delivery_type
            customer.preferred_courier = data.preferred_courier
            customer.other_transport_name = data.other_transport_name
            customer.preferred_rate = data.preferred_rate
            customer.email = data.email
            customer.gst_number = data.gst_number
            customer.notes = data.notes
            addresses = {address.address_type: address for address in customer.addresses}
            for address_type, value in (
                ("billing", data.billing_address),
                ("shipping", data.shipping_address),
            ):
                address = addresses.get(address_type)
                if address is None:
                    address = CustomerAddress(address_type=address_type)
                    customer.addresses.append(address)
                for field, field_value in self._address_values(value).items():
                    setattr(address, field, field_value)
        return self.get(customer_id)

    def set_storage(
        self,
        customer_id: int,
        *,
        storage_prefix: str,
        google_drive_folder_id: str | None = None,
    ) -> Customer | None:
        with session_scope(self._session_factory) as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                return None
            customer.storage_prefix = storage_prefix
            if google_drive_folder_id is not None:
                customer.google_drive_folder_id = google_drive_folder_id
        return self.get(customer_id)

    def create_storage_date(
        self,
        customer_id: int,
        folder_date: date,
    ) -> CustomerStorageDate | None:
        with session_scope(self._session_factory) as session:
            if session.get(Customer, customer_id) is None:
                return None
            existing = session.scalar(
                select(CustomerStorageDate).where(
                    CustomerStorageDate.customer_id == customer_id,
                    CustomerStorageDate.folder_date == folder_date,
                )
            )
            if existing is not None:
                return existing
            record = CustomerStorageDate(
                customer_id=customer_id,
                folder_date=folder_date,
            )
            session.add(record)
            session.flush()
            session.expunge(record)
            return record

    def list_storage_dates(self, customer_id: int) -> list[CustomerStorageDate]:
        with session_scope(self._session_factory) as session:
            return list(
                session.scalars(
                    select(CustomerStorageDate)
                    .where(CustomerStorageDate.customer_id == customer_id)
                    .order_by(CustomerStorageDate.folder_date.desc())
                )
            )

    def set_storage_date_drive_id(
        self,
        customer_id: int,
        folder_date: date,
        drive_folder_id: str,
    ) -> None:
        with session_scope(self._session_factory) as session:
            record = session.scalar(
                select(CustomerStorageDate).where(
                    CustomerStorageDate.customer_id == customer_id,
                    CustomerStorageDate.folder_date == folder_date,
                )
            )
            if record is not None:
                record.google_drive_folder_id = drive_folder_id

    def deactivate(self, customer_id: int) -> bool:
        with session_scope(self._session_factory) as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                return False
            customer.is_active = False
            return True

    def delete(self, customer_id: int) -> bool:
        with session_scope(self._session_factory) as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                return False
            session.delete(customer)
            return True

    def add_file_reference(
        self, customer_id: int, *, label: str, stored_path: str
    ) -> CustomerFileReference | None:
        with session_scope(self._session_factory) as session:
            if session.get(Customer, customer_id) is None:
                return None
            reference = CustomerFileReference(
                customer_id=customer_id, label=label, stored_path=stored_path
            )
            session.add(reference)
            session.flush()
            return reference

    @staticmethod
    def _build_addresses(data: CustomerInput) -> list[CustomerAddress]:
        return [
            CustomerAddress(
                address_type="billing",
                **CustomerRepository._address_values(data.billing_address),
            ),
            CustomerAddress(
                address_type="shipping",
                **CustomerRepository._address_values(data.shipping_address),
            ),
        ]

    @staticmethod
    def _address_values(address: AddressInput) -> dict[str, str]:
        return {
            "line1": address.line1,
            "line2": address.line2,
            "city": address.city,
            "landmark": address.landmark,
            "district": address.district,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
        }
