from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.modules.cloud_storage import CloudStorageService, LocalStorageProvider
from app.modules.customers import (
    AddressInput,
    CustomerInput,
    CustomerRepository,
    CustomerService,
    CustomerStorageDateExistsError,
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
    assert created.summary.display_identifier == "CUS-001 - KMS TEXTILES - CHENNAI"
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


def test_customer_mutations_trigger_configured_sheet_sync(tmp_path: Path) -> None:
    class RecordingSheetSync:
        def __init__(self) -> None:
            self.sync_count = 0
            self.is_connected = True
            self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/test/edit"

        def sync(self) -> None:
            self.sync_count += 1

    engine = create_database_engine(f"sqlite:///{tmp_path / 'customer-sync.db'}")
    Base.metadata.create_all(engine)
    sync = RecordingSheetSync()
    service = CustomerService(
        CustomerRepository(create_session_factory(engine)),
        sheet_sync=sync,  # type: ignore[arg-type]
    )

    created = service.create_customer(valid_customer())
    service.update_customer(
        created.summary.id,
        replace(valid_customer(), name="Synced Customer"),
    )
    service.deactivate_customer(created.summary.id)
    service.delete_customer(created.summary.id)

    assert sync.sync_count == 4
    engine.dispose()


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


def test_customer_creation_prepares_logical_storage_without_network_wait(
    tmp_path: Path,
) -> None:
    class CountingProvider(LocalStorageProvider):
        online_checks = 0

        def is_online(self) -> bool:
            self.online_checks += 1
            return super().is_online()

    engine = create_database_engine(f"sqlite:///{tmp_path / 'customer-storage.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    provider = CountingProvider(tmp_path / "backblaze")
    cloud = CloudStorageService(
        factory,
        provider,
        tmp_path / "cache",
    )
    service = CustomerService(CustomerRepository(factory), storage_service=cloud)

    created = service.create_customer(valid_customer("CO0001"))

    assert created.storage_prefix == "customers/CO0001 - KMS TEXTILES - CHENNAI"
    assert provider.online_checks == 0
    today = date.today().isoformat()
    assert service.customer_storage_dates(created.summary.id) == []
    assert provider.online_checks == 0
    assert service.create_customer_date_folder(created.summary.id) == today
    assert service.customer_storage_dates(created.summary.id) == [today]
    cloud.synchronize_async().result(timeout=5)
    markers_before = cloud.list_prefix(
        created.storage_prefix,
        include_markers=True,
    )
    assert len(markers_before) == 4

    with pytest.raises(CustomerStorageDateExistsError, match="already exists"):
        service.create_customer_date_folder(created.summary.id)
    assert len(cloud.list_prefix(created.storage_prefix, include_markers=True)) == 4

    design = tmp_path / "front-design.png"
    design.write_bytes(b"pixels")
    uploaded = service.upload_customer_file(
        created.summary.id,
        today,
        "Design",
        design,
    )
    assert uploaded.transfer_state == "queued"
    cloud.synchronize_async().result(timeout=5)
    assert cloud.get(uploaded.id).transfer_state == "synced"
    assert service.list_customer_files(created.summary.id, today, "Design")[0].id == uploaded.id
    assert service.customer_file_url(uploaded.id).startswith("file:")
    cloud.close()
    engine.dispose()
