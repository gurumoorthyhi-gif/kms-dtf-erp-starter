from types import SimpleNamespace

from app.ui.pages import OrderCreationDialog, OrdersPage


def test_order_intake_only_collects_customer_type_priority_and_due_date(qtbot) -> None:
    class CustomerService:
        def list_customers(self):
            return [
                SimpleNamespace(
                    id=7,
                    code="CR0007",
                    name="Customer Seven",
                    display_identifier="CR0007 - CUSTOMER SEVEN - CHENNAI",
                )
            ]

    dialog = OrderCreationDialog(CustomerService(), None)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog.order_type.setCurrentText("T-Shirt")
    dialog.priority.setCurrentText("High")

    data = dialog.order_input()

    assert dialog.customer.currentText() == "CR0007 - CUSTOMER SEVEN - CHENNAI"
    assert not hasattr(dialog, "customer_number")
    assert data.customer_id == 7
    assert data.order_type == "T-Shirt"
    assert data.priority == "High"
    assert data.items == ()
    assert not hasattr(dialog, "advance")
    assert not hasattr(dialog, "product")


def test_order_panel_shows_full_customer_and_quick_status_selection(qtbot) -> None:
    changed: list[tuple[int, str]] = []
    order = SimpleNamespace(
        id=4,
        order_number="KMS-20260729-0001",
        customer_display_identifier="CR0007 - CUSTOMER SEVEN - CHENNAI",
        order_type="DTF",
        status="Draft",
    )

    class OrderService:
        def list_orders(self, query=""):
            return [order]

        def change_status(self, order_id, status, note=""):
            changed.append((order_id, status))

    page = OrdersPage(
        OrderService(),  # type: ignore[arg-type]
        SimpleNamespace(),
        SimpleNamespace(),
    )
    qtbot.addWidget(page)
    changes: list[bool] = []
    page.order_changed.connect(lambda: changes.append(True))

    assert page.table.columnCount() == 4
    assert [
        page.table.horizontalHeaderItem(column).text() for column in range(4)
    ] == ["Order", "Customer", "Product type", "Status"]
    assert page.table.item(0, 1).text() == "CR0007 - CUSTOMER SEVEN - CHENNAI"

    status = page.table.cellWidget(0, 3)
    status.setCurrentText("Printing")

    assert changed == [(4, "Printing")]
    assert changes == [True]


def test_order_panel_hides_reverse_status_choices(qtbot) -> None:
    order = SimpleNamespace(
        id=5,
        order_number="KMS-20260729-0002",
        customer_display_identifier="CR0008 - CUSTOMER EIGHT - SALEM",
        order_type="T-Shirt",
        status="Printing",
    )

    class OrderService:
        def list_orders(self, query=""):
            return [order]

        def change_status(self, order_id, status, note=""):
            raise AssertionError("No transition expected")

    page = OrdersPage(
        OrderService(),  # type: ignore[arg-type]
        SimpleNamespace(),
        SimpleNamespace(),
    )
    qtbot.addWidget(page)
    status = page.table.cellWidget(0, 3)

    assert [status.itemText(index) for index in range(status.count())] == [
        "Printing",
        "Completed",
    ]
    assert status.findText("Designing") == -1
