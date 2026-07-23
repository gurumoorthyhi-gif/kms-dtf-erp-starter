from app.modules.customers import CustomerSummary
from app.ui.pages import CustomerFormDialog, CustomersPage


class FakeCustomerService:
    def __init__(self) -> None:
        self.queries: list[tuple[str, bool | None]] = []

    def list_customers(self, query: str = "", *, active: bool | None = True):
        self.queries.append((query, active))
        return [
            CustomerSummary(
                id=1,
                code="CUS-001",
                name="Customer One",
                business_name="Business One",
                phone="9876543210",
                email="one@example.com",
                is_active=True,
            )
        ]


def test_customer_page_loads_and_filters_service_data(qtbot) -> None:
    service = FakeCustomerService()
    page = CustomersPage(service)  # type: ignore[arg-type]
    qtbot.addWidget(page)

    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "CUS-001"

    page.search_input.setText("Business")

    assert service.queries[-1] == ("Business", True)


def test_customer_form_builds_typed_input(qtbot) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.code.setText("CUS-002")
    dialog.name.setText("Customer Two")
    dialog.phone.setText("9876543210")

    data = dialog.customer_input()

    assert data.code == "CUS-002"
    assert data.name == "Customer Two"
    assert data.billing_address.country == "India"
