from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.modules.customers import (
    AddressInput,
    CustomerInput,
    CustomerRepository,
    CustomerService,
    CustomerValidationError,
    DuplicateCustomerCodeError,
)


@pytest.fixture
def customer_service(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'customers.db'}")
    Base.metadata.create_all(engine)
    service = CustomerService(CustomerRepository(create_session_factory(engine)))
    yield service
    engine.dispose()


def valid_customer(code: str = "CUS-001") -> CustomerInput:
    return CustomerInput(
        code=code,
        name="KMS Customer",
        business_name="KMS Textiles",
        phone="+91 98765-43210",
        whatsapp_number="9876543210",
        preferred_rate=Decimal("35.50"),
        email="Owner@Example.com",
        gst_number="33ABCDE1234F1Z5",
        billing_address=AddressInput(
            line1="1 Market Road",
            city="Chennai",
            landmark="Near Central Station",
            district="Chennai",
            state="Tamil Nadu",
            postal_code="600001",
        ),
        shipping_address=AddressInput(
            line1="2 Factory Road",
            city="Chennai",
            district="Chengalpattu",
            state="Tamil Nadu",
            postal_code="600002",
        ),
        notes="Priority customer",
    )


def test_create_search_edit_and_deactivate_customer(customer_service) -> None:
    created = customer_service.create_customer(valid_customer())

    assert created.summary.code == "CUS-001"
    assert created.summary.phone == "+919876543210"
    assert created.summary.email == "owner@example.com"
    assert created.summary.preferred_rate == Decimal("35.50")
    assert created.billing_address.district == "Chennai"
    assert created.billing_address.landmark == "Near Central Station"
    assert created.shipping_address.district == "Chengalpattu"
    assert customer_service.list_customers("textiles")[0].id == created.summary.id

    updated = customer_service.update_customer(
        created.summary.id,
        replace(valid_customer(), name="Updated Customer"),
    )
    assert updated.summary.name == "Updated Customer"

    customer_service.deactivate_customer(created.summary.id)
    assert customer_service.list_customers() == []
    assert customer_service.list_customers(active=False)[0].is_active is False


def test_customer_can_be_permanently_deleted(customer_service) -> None:
    created = customer_service.create_customer(valid_customer())

    customer_service.delete_customer(created.summary.id)

    assert customer_service.list_customers(active=None) == []


def test_duplicate_code_is_rejected(customer_service) -> None:
    customer_service.create_customer(valid_customer())

    with pytest.raises(DuplicateCustomerCodeError):
        customer_service.create_customer(valid_customer("cus-001"))


def test_customer_codes_use_delivery_prefix_and_shared_sequence(customer_service) -> None:
    local = customer_service.create_customer(
        replace(valid_customer(), code="", delivery_type="Local")
    )
    courier = customer_service.create_customer(
        replace(
            valid_customer(),
            code="",
            name="Courier Customer",
            phone="9876543211",
            delivery_type="Courier",
        )
    )

    assert local.summary.code == "LO0001"
    assert local.summary.delivery_type == "Local"
    assert courier.summary.code == "CO0002"
    assert courier.summary.delivery_type == "Courier"

    changed = customer_service.update_customer(
        local.summary.id,
        replace(valid_customer(), code=local.summary.code, delivery_type="Courier"),
    )
    assert changed.summary.code == "CO0003"


def test_other_transport_requires_and_stores_transport_name(customer_service) -> None:
    with pytest.raises(CustomerValidationError, match="other transport name"):
        customer_service.create_customer(
            replace(
                valid_customer(),
                preferred_courier="OTHER TRANSPORT",
                other_transport_name="",
            )
        )

    created = customer_service.create_customer(
        replace(
            valid_customer(),
            preferred_courier="OTHER TRANSPORT",
            other_transport_name="KPN Travels",
        )
    )

    assert created.summary.preferred_courier == "OTHER TRANSPORT"
    assert created.summary.other_transport_name == "KPN Travels"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "invalid-email"),
        ("phone", "123"),
        ("gst_number", "INVALID"),
        ("code", "?"),
    ],
)
def test_customer_validation_rejects_invalid_values(
    customer_service, field: str, value: str
) -> None:
    with pytest.raises(CustomerValidationError):
        customer_service.create_customer(replace(valid_customer(), **{field: value}))


def test_customer_file_references_require_managed_relative_paths(customer_service) -> None:
    customer = customer_service.create_customer(valid_customer())
    customer_service.add_file_reference(
        customer.summary.id,
        "GST certificate",
        "customers/1/gst-certificate.pdf",
    )

    details = customer_service.get_customer(customer.summary.id)
    assert details.file_references == (("GST certificate", "customers/1/gst-certificate.pdf"),)

    with pytest.raises(CustomerValidationError):
        customer_service.add_file_reference(customer.summary.id, "Unsafe", "../secret.txt")
