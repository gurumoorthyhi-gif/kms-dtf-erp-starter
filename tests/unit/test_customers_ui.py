from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from app.modules.customers import CustomerSummary, CustomerValidationError
from app.ui.pages import (
    CustomerFolderDialog,
    CustomerFormDialog,
    CustomerImageEditorDialog,
    CustomersPage,
)


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


def test_customer_form_save_copies_confirmed_phone_and_billing_details(qtbot, monkeypatch) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.name.setText("Customer Two")
    dialog.phone.setText("9876543210")
    dialog.billing.village_city.setText("Chennai")
    dialog.billing.landmark.setText("Near Central Station")
    dialog.billing.district.setText("Chennai")
    dialog.billing.state.setCurrentText("Tamil Nadu")
    dialog.preferred_courier.setCurrentText("OTHER TRANSPORT")
    dialog.other_transport_name.setText("KPN Travels")
    dialog.preferred_rate.setText("42.75")
    saved = []
    dialog.set_save_operation(saved.append)
    monkeypatch.setattr(
        "app.ui.pages.customers.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    dialog.buttons.button(QDialogButtonBox.StandardButton.Save).click()

    data = saved[0]
    assert not hasattr(dialog, "same_as_phone_button")
    assert not hasattr(dialog, "same_as_billing_button")
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


def test_customer_form_no_confirmation_keeps_form_open_for_separate_details(
    qtbot, monkeypatch
) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.phone.setText("9876543210")
    dialog.billing.village_city.setText("Chennai")
    saved = []
    dialog.set_save_operation(saved.append)
    monkeypatch.setattr(
        "app.ui.pages.customers.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.No,
    )

    dialog.buttons.button(QDialogButtonBox.StandardButton.Save).click()
    qtbot.wait(10)

    assert saved == []
    assert dialog.isVisible()
    assert dialog.whatsapp.hasFocus()
    assert dialog.whatsapp.text() == ""
    assert dialog.shipping.village_city.text() == ""

    dialog.whatsapp.setText("9123456780")
    dialog.shipping.village_city.setText("Salem")
    dialog.buttons.button(QDialogButtonBox.StandardButton.Save).click()

    assert saved[0].whatsapp_number == "9123456780"
    assert saved[0].shipping_address.city == "Salem"


def test_customer_form_stays_open_when_save_validation_fails(qtbot, monkeypatch) -> None:
    dialog = CustomerFormDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    warnings: list[tuple[str, str]] = []
    attempts = 0

    def save_customer(data) -> None:
        nonlocal attempts
        attempts += 1
        if not data.name.strip():
            raise CustomerValidationError("Customer name is required")

    monkeypatch.setattr(
        "app.ui.pages.customers.QMessageBox.warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )
    monkeypatch.setattr(
        "app.ui.pages.customers.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    dialog.set_save_operation(save_customer)

    dialog.buttons.button(QDialogButtonBox.StandardButton.Save).click()

    assert dialog.isVisible()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert warnings == [("Customer not saved", "Customer name is required")]

    dialog.name.setText("Corrected Customer")
    dialog.buttons.button(QDialogButtonBox.StandardButton.Save).click()

    assert attempts == 2
    assert dialog.result() == QDialog.DialogCode.Accepted


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
    assert dialog.table.horizontalHeaderItem(0).text() == "Select"
    assert dialog.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert dialog.create_today_button.text() == "Create Folders"
    assert dialog.tree.currentItem().text(0) == "Design"
    assert dialog.upload_button.isEnabled()
    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0).child(1))
    assert dialog.tree.currentItem().text(0) == "Gangsheet"
    assert not dialog.upload_button.isEnabled()
    assert dialog.search_files_button.toolTip() == ("Search all customers by design number or date")
    assert dialog.image_search_button.toolTip() == "Search all customers using an image"
    assert [
        button.text()
        for button in (
            dialog.upload_button,
            dialog.edit_button,
            dialog.copy_to_button,
            dialog.delete_file_button,
        )
    ] == ["Upload", "Edit", "Copy To", "Delete"]


def test_customer_file_download_preserves_original_format(qtbot, tmp_path, monkeypatch) -> None:
    source = tmp_path / "design.png"
    source.write_bytes(b"image")
    downloaded: list[Path] = []
    cloud_file = SimpleNamespace(
        id=9,
        original_name="design.png",
        local_path=str(source),
        size_bytes=source.stat().st_size,
        transfer_state="synced",
        created_at=datetime.now(),
    )

    class DownloadService:
        def ensure_customer_storage(self, customer_id):
            return SimpleNamespace(
                summary=SimpleNamespace(display_identifier="CO0001 - KMS - TIRUPUR")
            )

        def customer_storage_dates(self, customer_id):
            return ["2026-07-29"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return [cloud_file]

        def download_customer_file(self, file_id, destination):
            downloaded.append(destination)
            return destination

    monkeypatch.setattr(
        "app.ui.pages.customers.QFileDialog.getSaveFileName",
        lambda *args: (str(tmp_path / "renamed.jpg"), "PNG file (*.png)"),
    )
    dialog = CustomerFolderDialog(DownloadService(), 1)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)

    dialog.download_file()

    assert downloaded == [tmp_path / "renamed.png"]


def test_customer_image_editor_contains_planned_tool_buttons(qtbot, tmp_path) -> None:
    image_path = tmp_path / "design.png"
    pixmap = QPixmap(200, 120)
    pixmap.fill(QColor("#6048E8"))
    assert pixmap.save(str(image_path))
    record = SimpleNamespace(original_name="design.png", local_path=str(image_path))

    editor = CustomerImageEditorDialog(record)
    qtbot.addWidget(editor)

    assert list(editor.tool_buttons) == [
        "BG Remove",
        "Upscale",
        "Eraser",
        "Select",
        "Colour Change",
    ]
    assert editor.preview.pixmap().isNull() is False


def test_customer_files_support_batch_download_and_copy_to(qtbot, tmp_path, monkeypatch) -> None:
    downloaded: list[tuple[int, Path]] = []
    pasted: list[tuple[int, int, str, str]] = []
    files = [
        SimpleNamespace(
            id=file_id,
            original_name=name,
            local_path=str(tmp_path / name),
            size_bytes=10,
            transfer_state="synced",
            created_at=datetime.now(),
        )
        for file_id, name in ((11, "front.png"), (12, "back.png"))
    ]

    class BatchService:
        def ensure_customer_storage(self, customer_id):
            return SimpleNamespace(
                summary=SimpleNamespace(display_identifier="CO0001 - KMS - TIRUPUR")
            )

        def customer_storage_dates(self, customer_id):
            return ["2026-07-29"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return files

        def download_customer_file(self, file_id, destination):
            downloaded.append((file_id, destination))

        def copy_customer_file(self, file_id, customer_id, date_name, folder_name):
            pasted.append((file_id, customer_id, date_name, folder_name))

    monkeypatch.setattr(
        "app.ui.pages.customers.QFileDialog.getExistingDirectory",
        lambda *args: str(tmp_path / "downloads"),
    )

    class FakeCopyDestination:
        def __init__(self, service, parent):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def destination(self):
            return (2, "2026-07-30", "Design")

    monkeypatch.setattr(
        "app.ui.pages.customers.CopyFilesToDialog",
        FakeCopyDestination,
    )
    dialog = CustomerFolderDialog(BatchService(), 1)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    dialog.table.item(1, 0).setCheckState(Qt.CheckState.Checked)

    dialog.download_file()
    dialog.copy_files_to()

    assert downloaded == [
        (11, tmp_path / "downloads" / "front.png"),
        (12, tmp_path / "downloads" / "back.png"),
    ]
    assert pasted == [
        (11, 2, "2026-07-30", "Design"),
        (12, 2, "2026-07-30", "Design"),
    ]


def test_customer_folder_opens_in_separate_maximized_window(qtbot) -> None:
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
    assert page._folder_workspace.windowState() & Qt.WindowState.WindowMaximized

    page._folder_workspace.small_window_button.click()
    assert not page._folder_workspace.windowState() & Qt.WindowState.WindowMaximized

    page._folder_workspace.maximize_window_button.click()
    assert page._folder_workspace.windowState() & Qt.WindowState.WindowMaximized

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
    assert dialog.tree.topLevelItem(0).text(0) == "1. CUS-001 - BUSINESS ONE - CHENNAI"

    dialog.tree_back_button.click()
    assert dialog.tree.topLevelItem(0).text(0) == "Customers"
    assert dialog.tree_back_button.isEnabled() is False


def test_customer_folder_tree_lists_and_opens_other_customers(qtbot) -> None:
    first = CustomerSummary(
        id=1,
        code="CO0001",
        display_identifier="CO0001 - KMS - TIRUPUR",
        name="KMS",
        business_name="KMS",
        phone="9876543210",
        whatsapp_number="",
        delivery_type="Local",
        preferred_courier="",
        other_transport_name="",
        preferred_rate=Decimal("0"),
        email=None,
        is_active=True,
    )
    second = CustomerSummary(
        id=2,
        code="CO0002",
        display_identifier="CO0002 - SECOND CUSTOMER - CHENNAI",
        name="Second Customer",
        business_name="Second Customer",
        phone="9876543211",
        whatsapp_number="",
        delivery_type="Local",
        preferred_courier="",
        other_transport_name="",
        preferred_rate=Decimal("0"),
        email=None,
        is_active=True,
    )

    class MultiCustomerFolderService:
        def list_customers(self, query="", *, active=True):
            return [first, second]

        def ensure_customer_storage(self, customer_id):
            summary = first if customer_id == 1 else second
            return SimpleNamespace(summary=summary)

        def customer_storage_dates(self, customer_id):
            return ["2026-07-28"] if customer_id == 1 else ["2026-07-29"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return []

    dialog = CustomerFolderDialog(MultiCustomerFolderService(), 1)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)

    dialog.tree_back_button.click()

    assert dialog.tree.topLevelItemCount() == 2
    assert dialog.tree.topLevelItem(0).text(0) == f"1. {first.display_identifier}"
    assert dialog.tree.topLevelItem(1).text(0) == f"2. {second.display_identifier}"

    second_item = dialog.tree.topLevelItem(1)
    dialog._open_tree_item(second_item, 0)

    assert dialog._customer_id == 2
    assert dialog.heading.text() == second.display_identifier
    assert dialog.tree.topLevelItem(0).text(0) == "2026-07-29"
