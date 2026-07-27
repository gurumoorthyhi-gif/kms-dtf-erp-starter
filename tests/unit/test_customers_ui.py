from decimal import Decimal

from PySide6.QtCore import Qt

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
                display_identifier="CUS-001 - BUSINESS ONE - CHENNAI",
                name="Customer One",
                business_name="Business One",
                phone="9876543210",
                whatsapp_number="9876543210",
                delivery_type="Courier",
                preferred_courier="DTDC",
                other_transport_name="",
                preferred_rate=Decimal("125.50"),
                email="one@example.com",
                is_active=True,
            )
        ]


def test_customer_page_loads_and_filters_service_data(qtbot) -> None:
    service = FakeCustomerService()
    page = CustomersPage(service)  # type: ignore[arg-type]
    qtbot.addWidget(page)

    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "CUS-001 - BUSINESS ONE - CHENNAI"
    assert page.table.item(0, 1).text() == "Customer One"
    assert page.table.item(0, 4).text() == "DTDC"
    assert page.table.cellWidget(0, 5).text() == "Details"

    page.search_input.setText("Business")

    assert service.queries[-1] == ("Business", True)


def test_customer_form_builds_typed_input(qtbot) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.name.setText("Customer Two")
    dialog.phone.setText("9876543210")
    dialog.same_as_phone_button.click()
    dialog.billing.village_city.setText("Chennai")
    dialog.billing.landmark.setText("Near Central Station")
    dialog.billing.district.setText("Chennai")
    dialog.billing.state.setCurrentText("Tamil Nadu")
    dialog.same_as_billing_button.click()
    dialog.preferred_courier.setCurrentText("OTHER TRANSPORT")
    dialog.other_transport_name.setText("KPN Travels")
    dialog.preferred_rate.setText("42.75")

    data = dialog.customer_input()

    assert data.code == ""
    assert data.name == "Customer Two"
    assert data.whatsapp_number == "9876543210"
    assert data.delivery_type == "Courier"
    assert data.preferred_courier == "OTHER TRANSPORT"
    assert data.other_transport_name == "KPN Travels"
    assert data.preferred_rate == Decimal("42.75")
    assert data.billing_address.country == "India"
    assert data.shipping_address.city == "Chennai"
    assert data.shipping_address.landmark == "Near Central Station"
    assert data.shipping_address.district == "Chennai"
    assert data.shipping_address.state == "Tamil Nadu"


def test_address_state_field_provides_india_prefix_completion(qtbot) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)

    states = [
        dialog.billing.state.itemText(index)
        for index in range(dialog.billing.state.count())
    ]

    assert dialog.billing.state.isEditable()
    assert dialog.billing.state.completer().filterMode() == Qt.MatchFlag.MatchStartsWith
    assert {"Tamil Nadu", "Telangana", "Tripura"} <= set(states)
    assert dialog.billing.country.isReadOnly()


def test_pincode_autofills_district_and_state_without_overwriting_locality(qtbot) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.billing.village_city.setText("Sowcarpet")

    dialog.billing.postal_code.setText("600001")

    assert dialog.billing.village_city.text() == "Sowcarpet"
    assert dialog.billing.district.text() == "Chennai"
    assert dialog.billing.state.currentText() == "Tamil Nadu"


def test_local_delivery_hides_and_clears_courier_fields(qtbot) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.name.setText("Local Customer")
    dialog.phone.setText("9876543210")
    dialog.preferred_courier.setCurrentText("DTDC")

    dialog.delivery_type.setCurrentText("Local")
    data = dialog.customer_input()

    assert dialog.preferred_courier.isHidden()
    assert dialog.other_transport_name.isHidden()
    assert data.preferred_courier == ""
    assert data.other_transport_name == ""
