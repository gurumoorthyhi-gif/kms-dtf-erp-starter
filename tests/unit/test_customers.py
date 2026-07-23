from dataclasses import replace
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
        email="Owner@Example.com",
        gst_number="33ABCDE1234F1Z5",
        billing_address=AddressInput(
            line1="1 Market Road",
            city="Chennai",
            state="Tamil Nadu",
            postal_code="600001",
        ),
        shipping_address=AddressInput(
            line1="2 Factory Road",
            city="Chennai",
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
    assert customer_service.list_customers("textiles")[0].id == created.summary.id

    updated = customer_service.update_customer(
        created.summary.id,
        replace(valid_customer(), name="Updated Customer"),
    )
    assert updated.summary.name == "Updated Customer"

    customer_service.deactivate_customer(created.summary.id)
    assert customer_service.list_customers() == []
    assert customer_service.list_customers(active=False)[0].is_active is False


def test_duplicate_code_is_rejected(customer_service) -> None:
    customer_service.create_customer(valid_customer())

    with pytest.raises(DuplicateCustomerCodeError):
        customer_service.create_customer(valid_customer("cus-001"))


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
