from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image

from app.database import Base, create_database_engine, create_session_factory
from app.modules.artwork import (
    ArtworkInput,
    ArtworkRepository,
    ArtworkService,
    ArtworkStorage,
    PreviewService,
)
from app.modules.customers import CustomerInput, CustomerRepository, CustomerService
from app.modules.orders import OrderInput, OrderItemInput, OrderRepository, OrderService
from app.modules.products import ProductInput, ProductRepository, ProductService


@pytest.fixture
def artwork_context(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'artwork.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    customers = CustomerService(CustomerRepository(factory))
    products = ProductService(ProductRepository(factory))
    customer = customers.create_customer(CustomerInput("CUS-001", "KMS Customer", "9876543210"))
    category_id, _ = products.create_category("DTF")
    product = products.create_product(
        ProductInput("DTF-M", "DTF", category_id, "metre", Decimal("100"), Decimal("18"))
    )
    orders = OrderService(OrderRepository(factory), products)
    order = orders.create_order(
        OrderInput(
            customer.summary.id,
            (OrderItemInput(product.id, Decimal("1")),),
        )
    )
    storage = ArtworkStorage(tmp_path / "managed-artwork", PreviewService())
    service = ArtworkService(ArtworkRepository(factory), storage)
    yield service, storage, customer.summary.id, order.summary.id, tmp_path
    engine.dispose()


def make_image(path: Path, size: tuple[int, int], *, transparent: bool) -> bytes:
    mode = "RGBA" if transparent else "RGB"
    colour = (100, 20, 220, 100) if transparent else (100, 20, 220)
    Image.new(mode, size, colour).save(path, dpi=(300, 300))
    return path.read_bytes()


def test_upload_preserves_original_and_generates_optimized_preview(artwork_context) -> None:
    service, storage, customer_id, order_id, tmp_path = artwork_context
    source = tmp_path / "customer-logo.png"
    original_bytes = make_image(source, (1200, 800), transparent=True)

    details = service.upload(
        ArtworkInput(
            "Customer logo",
            source,
            ("Logo", " repeat-order "),
            customer_id,
            order_id,
            "Original supplied by customer",
        )
    )

    latest = details.summary.latest_version
    assert details.summary.customer_name == "KMS Customer"
    assert details.summary.order_number
    assert details.summary.tags == ("logo", "repeat-order")
    assert latest.width == 1200 and latest.height == 800
    assert latest.has_transparency is True
    assert Path(latest.original_path).is_absolute() is False
    assert storage.resolve(latest.original_path).read_bytes() == original_bytes
    with Image.open(service.preview_file(latest.preview_path)) as preview:
        assert preview.width <= 640 and preview.height <= 640


def test_search_new_version_and_approval_history(artwork_context) -> None:
    service, _, customer_id, order_id, tmp_path = artwork_context
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    make_image(first, (400, 300), transparent=False)
    make_image(second, (800, 600), transparent=False)
    created = service.upload(ArtworkInput("Front Print", first, ("tshirt",), customer_id, order_id))

    versioned = service.add_version(created.summary.id, second, "Higher resolution")
    approved = service.record_approval(
        versioned.summary.latest_version.id,
        "Approved",
        "Customer confirmed",
    )

    assert len(approved.versions) == 2
    assert approved.summary.latest_version.version_number == 2
    assert approved.summary.latest_version.approval_status == "Approved"
    assert service.list_artwork("tshirt")[0].id == created.summary.id
    assert service.list_artwork("KMS Customer")[0].id == created.summary.id


def test_managed_path_cannot_escape_storage(artwork_context) -> None:
    service, _, _, _, _ = artwork_context
    with pytest.raises(ValueError):
        service.preview_file("../outside.png")
