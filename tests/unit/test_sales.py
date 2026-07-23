from decimal import Decimal
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.database import Base, create_database_engine, create_session_factory
from app.modules.customers import CustomerInput, CustomerRepository, CustomerService
from app.modules.inventory import (
    InventoryItemInput,
    InventoryRepository,
    InventoryService,
    PurchaseInput,
    PurchaseItemInput,
    PurchaseRepository,
    PurchaseService,
    SupplierInput,
)
from app.modules.orders import OrderInput, OrderItemInput, OrderRepository, OrderService
from app.modules.products import ProductInput, ProductRepository, ProductService
from app.modules.sales import PaymentInput, SalesRepository, SalesService


@pytest.fixture
def sales(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'sales.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    customers = CustomerService(CustomerRepository(factory))
    products = ProductService(ProductRepository(factory))
    customer = customers.create_customer(CustomerInput("CUS-001", "Customer", "9876543210"))
    category_id, _ = products.create_category("DTF")
    product = products.create_product(
        ProductInput("DTF-001", "DTF Print", category_id, "metre", Decimal("100"), Decimal("18"))
    )
    orders = OrderService(OrderRepository(factory), products)
    order = orders.create_order(
        OrderInput(customer.summary.id, (OrderItemInput(product.id, Decimal("10")),))
    )
    yield (
        SalesService(SalesRepository(factory)),
        order.summary.id,
        customer.summary.id,
        factory,
        tmp_path,
    )
    engine.dispose()


def test_quotation_conversion_preserves_quote_and_generates_invoice(sales) -> None:
    service, order_id, _, _, _ = sales
    quotation = service.create_quotation(order_id)
    invoice = service.convert_to_invoice(quotation.id)

    quotations = service.list_documents("Quotation")
    assert quotation.document_number.startswith("QUO-")
    assert quotations[0].status == "Converted"
    assert invoice.document_number.startswith("INV-")
    assert invoice.total == Decimal("1180.00")
    assert invoice.balance == invoice.total


def test_advance_part_payment_credit_and_customer_ledger(sales) -> None:
    service, order_id, customer_id, _, _ = sales
    invoice = service.generate_invoice(order_id)
    after_advance = service.record_payment(
        PaymentInput(invoice.id, Decimal("200"), "UPI", is_advance=True)
    )
    after_part = service.record_payment(
        PaymentInput(invoice.id, Decimal("300"), "Bank transfer", "BANK-1")
    )
    after_credit = service.issue_credit_note(invoice.id, Decimal("80"), "Price correction")

    assert after_advance.balance == Decimal("980.00")
    assert after_part.balance == Decimal("680.00")
    assert after_credit.balance == Decimal("600.00")
    assert [payment.payment_type for payment in service.list_payments()] == [
        "Payment",
        "Advance",
    ]
    ledger = service.customer_ledger(customer_id)
    assert ledger[-1].balance == Decimal("600.00")
    assert sum((entry.debit for entry in ledger), Decimal("0")) == Decimal("1180.00")
    assert sum((entry.credit for entry in ledger), Decimal("0")) == Decimal("580.00")


def test_payment_cannot_exceed_balance_and_audit_history_remains(sales) -> None:
    service, order_id, _, _, _ = sales
    invoice = service.generate_invoice(order_id)
    service.record_payment(PaymentInput(invoice.id, Decimal("100"), "Cash"))

    with pytest.raises(ValueError, match="cannot exceed"):
        service.record_payment(PaymentInput(invoice.id, Decimal("2000"), "Cash"))

    assert service.list_documents("Invoice")[0].balance == Decimal("1080.00")
    assert len(service.list_payments()) == 1


def test_invoice_pdf_is_exported(sales, qapp: QApplication) -> None:
    service, order_id, _, _, tmp_path = sales
    invoice = service.generate_invoice(order_id)

    output = service.export_pdf(invoice.id, tmp_path / "exports" / "invoice.pdf")

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")


def test_supplier_ledger_uses_decimal_purchase_totals(sales) -> None:
    service, _, _, factory, _ = sales
    inventory = InventoryService(InventoryRepository(factory))
    item = inventory.create_item(
        InventoryItemInput("FILM", "Film", "DTF film", "roll", unit_cost=Decimal("500"))
    )
    purchases = PurchaseService(PurchaseRepository(factory))
    supplier = purchases.create_supplier(SupplierInput("SUP-1", "Supplier"))
    purchase = purchases.create_purchase(
        PurchaseInput(
            supplier.id,
            (PurchaseItemInput(item.id, Decimal("2"), Decimal("500")),),
        )
    )

    ledger = service.supplier_ledger(supplier.id)

    assert ledger[0].reference == purchase.purchase_number
    assert ledger[0].credit == Decimal("1000.00")
    assert ledger[0].balance == Decimal("-1000.00")
