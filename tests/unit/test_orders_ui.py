from datetime import date
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QDialog, QPushButton

from app.ui.pages import OrderCreationDialog, OrdersPage
from app.ui.pages.orders import TransparentDesignPreview


def test_order_intake_only_collects_customer_and_product_type(qtbot) -> None:
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
    assert dialog.customer.currentText() == "Select customer"
    assert dialog.customer.currentData() is None
    dialog.customer.setCurrentIndex(1)
    dialog.order_type.setCurrentText("T-Shirt")

    data = dialog.order_input()

    assert dialog.customer.currentText() == "CR0007 - CUSTOMER SEVEN - CHENNAI"
    assert not hasattr(dialog, "customer_number")
    assert data.customer_id == 7
    assert data.order_type == "T-Shirt"
    assert data.priority == "Normal"
    assert data.due_date is None
    assert data.notes == ""
    assert data.items == ()
    assert not hasattr(dialog, "priority")
    assert not hasattr(dialog, "due_date")
    assert not hasattr(dialog, "notes")
    assert not hasattr(dialog, "advance")
    assert not hasattr(dialog, "product")


def test_order_intake_can_create_and_select_a_new_customer(qtbot, monkeypatch) -> None:
    customers = [
        SimpleNamespace(id=7, display_identifier="CR0007 - CUSTOMER SEVEN - CHENNAI")
    ]

    class CustomerService:
        def list_customers(self):
            return customers

        def create_customer(self, _customer_input):
            summary = SimpleNamespace(
                id=8,
                display_identifier="CR0008 - CUSTOMER EIGHT - SALEM",
            )
            customers.append(summary)
            return SimpleNamespace(summary=summary)

    class CustomerDialog:
        def __init__(self, parent=None):
            self.parent = parent
            self.save_operation = None

        def set_save_operation(self, operation):
            self.save_operation = operation

        def exec(self):
            self.save_operation(SimpleNamespace())
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("app.ui.pages.orders.CustomerFormDialog", CustomerDialog)
    dialog = OrderCreationDialog(CustomerService(), None)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)

    dialog.add_customer_button.click()

    assert dialog.customer.currentData() == 8
    assert dialog.customer.currentText() == "CR0008 - CUSTOMER EIGHT - SALEM"


def test_order_intake_imports_design_to_existing_or_new_today_folder(
    qtbot, monkeypatch, tmp_path
) -> None:
    design = tmp_path / "front.png"
    design.write_bytes(b"design")
    created_dates = []
    uploaded = []

    class CustomerService:
        def list_customers(self):
            return [SimpleNamespace(id=7, display_identifier="CR0007 - CUSTOMER SEVEN")]

        def customer_storage_dates(self, customer_id):
            assert customer_id == 7
            return []

        def next_customer_design_filenames(self, customer_id, source_names):
            assert customer_id == 7
            return [f"CR0007 - DE{index} - {name}" for index, name in enumerate(source_names, 1)]

        def create_customer_date_folder(self, customer_id):
            created_dates.append(customer_id)
            return date.today().isoformat()

        def upload_customer_file(self, customer_id, date_name, folder_name, source):
            uploaded.append((customer_id, date_name, folder_name, source))
            return SimpleNamespace(id=41)

    monkeypatch.setattr(
        "app.ui.pages.orders.QFileDialog.getOpenFileNames",
        lambda *args: ([str(design)], ""),
    )
    dialog = OrderCreationDialog(CustomerService(), None)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog.customer.setCurrentIndex(1)

    dialog.import_design_button.click()

    today = date.today().isoformat()
    assert created_dates == []
    assert uploaded == []
    assert dialog.import_design_status.text() == (
        "1 design(s) ready — files upload when you click Save"
    )
    assert dialog.design_preview.count() == 1
    assert dialog.design_preview.item(0).text() == ""
    assert dialog.design_preview.item(0).icon().isNull()
    assert dialog.design_preview.item(0).toolTip() == "CR0007 - DE1 - front.png"

    dialog._validate_and_accept()

    assert created_dates == [7]
    assert uploaded == [(7, today, "Design", Path(design))]
    assert dialog.order_input().design_file_ids == (41,)
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_order_design_can_be_removed_before_save(qtbot, tmp_path) -> None:
    source = tmp_path / "remove.png"
    source.write_bytes(b"preview")

    class CustomerService:
        def list_customers(self):
            return []

    dialog = OrderCreationDialog(CustomerService(), None)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog._add_design_preview(source)
    item = dialog.design_preview.item(0)
    tile = dialog.design_preview.itemWidget(item)
    remove_button = tile.findChild(QPushButton)

    remove_button.click()

    assert dialog.design_preview.count() == 0
    assert dialog._staged_designs == []
    assert dialog.import_design_status.text() == "No designs selected"


def test_saved_order_designs_can_be_opened_from_order_panel(qtbot, tmp_path) -> None:
    first = tmp_path / "front.png"
    second = tmp_path / "back.png"
    first.write_bytes(b"front")
    second.write_bytes(b"back")

    order = SimpleNamespace(
        id=4,
        order_number="KMS-20260802-0001",
        customer_display_identifier="CR0001 - KMS - TIRUPPUR",
        order_type="DTF",
        status="Draft",
    )

    class OrderService:
        def list_orders(self, query=""):
            return [order]

        def get_order(self, order_id):
            assert order_id == 4
            return SimpleNamespace(design_file_ids=(41, 42))

    records = {
        41: SimpleNamespace(
            local_path=str(first), original_name="CR0001 - DE1 - front.png"
        ),
        42: SimpleNamespace(
            local_path=str(second), original_name="CR0001 - DE2 - back.png"
        ),
    }
    customer_service = SimpleNamespace(customer_file=lambda file_id: records[file_id])
    dialog = OrdersPage(
        OrderService(),  # type: ignore[arg-type]
        customer_service,  # type: ignore[arg-type]
        SimpleNamespace(),
    )
    qtbot.addWidget(dialog)
    opened = []
    dialog.open_designs_requested.connect(opened.append)

    dialog.table.cellWidget(0, 3).click()

    assert [path.name for path, _file_id in opened[0]] == [
        "CR0001 - DE1 - front.png",
        "CR0001 - DE2 - back.png",
    ]
    assert [file_id for _path, file_id in opened[0]] == [41, 42]
    assert [path.read_bytes() for path, _file_id in opened[0]] == [b"front", b"back"]


def test_new_order_fields_require_customer_selection(qtbot, monkeypatch) -> None:
    warnings = []

    class CustomerService:
        def list_customers(self):
            return []

    monkeypatch.setattr(
        "app.ui.pages.orders.QMessageBox.warning",
        lambda _parent, title, message: warnings.append((title, message)),
    )
    dialog = OrderCreationDialog(CustomerService(), None)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)

    qtbot.mouseClick(dialog.order_type, Qt.MouseButton.LeftButton)
    dialog.import_design_button.click()
    dialog._validate_and_accept()

    assert warnings == [
        ("Select customer", "Select a customer first."),
        ("Select customer", "Select a customer before importing."),
        ("Select customer", "Select a customer first."),
    ]


def test_order_design_double_click_opens_large_preview(qtbot, monkeypatch, tmp_path) -> None:
    source = tmp_path / "transparent.png"
    source.write_bytes(b"preview")
    opened = []

    class PreviewDialog:
        def __init__(self, path, parent=None):
            opened.append((path, parent))

        def exec(self):
            return QDialog.DialogCode.Rejected

    class CustomerService:
        def list_customers(self):
            return []

    monkeypatch.setattr("app.ui.pages.orders.DesignPreviewDialog", PreviewDialog)
    dialog = OrderCreationDialog(CustomerService(), None)  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    dialog._add_design_preview(source)
    item = dialog.design_preview.item(0)

    qtbot.mouseDClick(dialog.design_preview.itemWidget(item), Qt.MouseButton.LeftButton)

    assert item.data(Qt.ItemDataRole.UserRole) == str(source)
    assert opened == [(source, dialog)]


def test_large_design_preview_has_checkerboard_and_interactive_zoom(qtbot, tmp_path) -> None:
    source = tmp_path / "alpha.png"
    image = QImage(80, 60, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    image.setPixelColor(20, 20, QColor("#FF3366"))
    assert image.save(str(source))
    preview = TransparentDesignPreview(source)
    qtbot.addWidget(preview)
    preview.resize(700, 500)
    preview.show()
    qtbot.wait(10)
    initial_scale = preview.transform().m11()

    preview._apply_zoom(1.18)

    assert preview.original.hasAlphaChannel()
    assert not preview.backgroundBrush().texture().isNull()
    assert preview.transform().m11() > initial_scale


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

    assert page.table.columnCount() == 5
    assert [page.table.horizontalHeaderItem(column).text() for column in range(5)] == [
        "Order",
        "Customer",
        "Product type",
        "Open design",
        "Status",
    ]
    assert page.table.item(0, 1).text() == "CR0007 - CUSTOMER SEVEN - CHENNAI"

    assert page.table.cellWidget(0, 3).text() == "Open design"
    status = page.table.cellWidget(0, 4)
    status.setCurrentText("Printing")

    assert changed == [(4, "Printing")]
    assert changes == [True]
    assert status.findText("Canceled") >= 0


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
    status = page.table.cellWidget(0, 4)

    assert [status.itemText(index) for index in range(status.count())] == [
        "Printing",
        "Completed",
        "Canceled",
    ]
    assert status.findText("Designing") == -1
    assert status.findText("Canceled") >= 0
