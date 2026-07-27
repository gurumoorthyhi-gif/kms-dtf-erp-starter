from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from app.modules.customers import CustomerSummary
from app.ui.pages import CustomerFolderDialog, CustomerFormDialog, CustomersPage


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
    assert page.table.cellWidget(0, 5).text() == "Open folder"

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

    states = [dialog.billing.state.itemText(index) for index in range(dialog.billing.state.count())]

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


def test_customer_folder_opens_maximized_with_adjustable_image_preview(
    qtbot,
    tmp_path,
) -> None:
    image_path = tmp_path / "design.png"
    pixmap = QPixmap(320, 180)
    pixmap.fill(QColor("#6048E8"))
    assert pixmap.save(str(image_path))
    summary = SimpleNamespace(display_identifier="CO0001 - KMS - TIRUPUR")
    details = SimpleNamespace(summary=summary)
    cloud_file = SimpleNamespace(
        id=7,
        original_name="design.png",
        local_path=str(image_path),
        size_bytes=image_path.stat().st_size,
        transfer_state="synced",
        created_at=datetime.now(),
    )

    class FolderService:
        def ensure_customer_storage(self, customer_id):
            assert customer_id == 1
            return details

        def customer_storage_dates(self, customer_id):
            return ["2026-07-28"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return [cloud_file] if folder_name == "Design" else []

    dialog = CustomerFolderDialog(FolderService(), 1)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.table.selectRow(0)
    qtbot.wait(50)

    assert dialog.windowState() & Qt.WindowState.WindowMaximized
    assert dialog.workspace_splitter.count() == 2
    assert dialog.workspace_splitter.widget(0) is dialog.browser_panel
    assert dialog.workspace_splitter.widget(1) is dialog.preview_panel
    assert dialog.browser_splitter.widget(0) is dialog.tree_panel
    assert dialog.workspace_splitter.handleWidth() > 0
    assert dialog.preview_stack.currentWidget() is dialog.image_scroll
    assert dialog.image_label.pixmap().isNull() is False


def test_customer_folder_opens_in_separate_full_screen_window(qtbot) -> None:
    class EmbeddedFolderService(FakeCustomerService):
        def ensure_customer_storage(self, customer_id):
            summary = SimpleNamespace(display_identifier="CO0001 - KMS - TIRUPUR")
            return SimpleNamespace(summary=summary)

        def customer_storage_dates(self, customer_id):
            return []

    page = CustomersPage(EmbeddedFolderService())  # type: ignore[arg-type]
    qtbot.addWidget(page)
    page.show()

    page.open_customer_folder(1)

    assert page._folder_workspace is not None
    assert page.page_stack.currentWidget() is page.customer_list_page
    assert page._folder_workspace._embedded is False
    assert page._folder_workspace.windowState() & Qt.WindowState.WindowFullScreen

    page._folder_workspace.close()


def test_customer_folder_tree_can_go_back_to_customer_and_main_folder(qtbot) -> None:
    class FolderService(FakeCustomerService):
        def ensure_customer_storage(self, customer_id):
            summary = SimpleNamespace(display_identifier="CO0001 - KMS - TIRUPUR")
            return SimpleNamespace(summary=summary)

        def customer_storage_dates(self, customer_id):
            return ["2026-07-28"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return []

    dialog = CustomerFolderDialog(FolderService(), 1)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)

    assert dialog.tree.topLevelItem(0).text(0) == "2026-07-28"

    dialog.tree_back_button.click()
    assert dialog.tree.topLevelItem(0).text(0) == "CO0001 - KMS - TIRUPUR"

    dialog.tree_back_button.click()
    assert dialog.tree.topLevelItem(0).text(0) == "Customers"
    assert dialog.tree_back_button.isEnabled() is False
