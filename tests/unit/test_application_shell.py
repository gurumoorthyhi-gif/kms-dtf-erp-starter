from types import SimpleNamespace

from PySide6.QtCore import QPoint, QRect, QRectF, QSettings, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPalette
from PySide6.QtWidgets import QTableWidgetSelectionRange

from app.ui.application import MainWindow, PageRouter
from app.ui.components import (
    ANIMATION_DURATION_MS,
    COLLAPSED_WIDTH,
    EXPANDED_WIDTH,
    Sidebar,
)
from app.ui.pages import DashboardPage, ImageEditorPage
from app.ui.pages.image_editor import CustomerImageDialog


def test_page_router_navigates_registered_pages(qtbot) -> None:
    router = PageRouter()
    dashboard = DashboardPage()
    router.register_page("dashboard", dashboard)
    qtbot.addWidget(router)

    router.navigate("dashboard")

    assert router.currentWidget() is dashboard
    assert router.current_page_name == "dashboard"


def test_sidebar_remains_collapsed(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.show()

    assert sidebar.width() == COLLAPSED_WIDTH
    assert EXPANDED_WIDTH == COLLAPSED_WIDTH == 78
    assert sidebar.animation_duration == ANIMATION_DURATION_MS == 200
    assert sidebar.is_expanded is False
    assert sidebar.is_pinned is False
    assert sidebar.button_for("dashboard").text() == ""
    assert sidebar.button_for("dashboard").toolTip() == "Dashboard"
    assert sidebar.button_for("users").toolTip() == "Users"

    sidebar.expand()
    qtbot.wait(250)
    assert sidebar.minimumWidth() == sidebar.maximumWidth() == COLLAPSED_WIDTH
    assert sidebar.button_for("dashboard").text() == ""

    sidebar.collapse()
    qtbot.wait(150)
    assert sidebar.minimumWidth() == sidebar.maximumWidth() == COLLAPSED_WIDTH


def test_sidebar_reuses_one_flyout_between_icons(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.show()
    dashboard = sidebar.button_for("dashboard")
    orders = sidebar.button_for("orders")
    flyout = sidebar._tooltip

    dashboard.hovered.emit(dashboard, True)
    qtbot.wait(220)
    assert flyout.isVisible()
    assert flyout._label.text() == "Dashboard"

    orders.hovered.emit(orders, True)
    qtbot.wait(220)
    assert sidebar._tooltip is flyout
    assert flyout._label.text() == "Orders"
    assert sidebar.minimumWidth() == sidebar.maximumWidth() == COLLAPSED_WIDTH

    flyout.fade_out()
    qtbot.wait(180)
    assert flyout.isVisible() is False


def test_sidebar_theme_toggle_changes_choice(qtbot) -> None:
    settings = QSettings("KMS", "DTF ERP")
    previous = settings.value("ui/theme")
    settings.setValue("ui/theme", "dark")
    try:
        sidebar = Sidebar()
        qtbot.addWidget(sidebar)
        assert sidebar._theme_button.toolTip() == "Switch to Light Mode"

        sidebar._theme_button.click()
        qtbot.wait(380)

        assert sidebar._dark_mode is False
        assert sidebar._theme_button.toolTip() == "Switch to Dark Mode"
    finally:
        if previous is None:
            settings.remove("ui/theme")
        else:
            settings.setValue("ui/theme", previous)


def test_main_window_routes_placeholder_pages(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowIcon().isNull() is False
    assert window.sidebar.minimumWidth() == window.sidebar.maximumWidth() == COLLAPSED_WIDTH
    assert window.router.current_page_name == "dashboard"
    assert window.top_bar.title == "Dashboard"
    assert window.sidebar.button_for("dashboard").property("active") is True

    window.navigate("settings")

    assert window.router.current_page_name == "settings"
    assert window.top_bar.title == "Settings"
    assert window.sidebar.button_for("settings").property("active") is True


def test_image_editor_page_shell_is_registered(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.navigate("image_editor")

    assert window.router.currentWidget() is window.image_editor_page
    assert window.top_bar.title == "Image Editor"
    assert window.sidebar.button_for("image_editor").toolTip() == "Image Editor"
    assert window.sidebar.button_for("image_editor").property("active") is True
    assert isinstance(window.image_editor_page, ImageEditorPage)
    assert len(window.image_editor_page.tool_labels) == 11
    assert window.image_editor_page.tool_labels["Background Remover"].property("active") is True
    assert window.image_editor_page.tool_labels["Background Remover"].text() == (
        "BACKGROUND REMOVER"
    )
    assert window.image_editor_page.tool_labels["Trace Bitmap"].text() == "TRACE BITMAP"
    assert window.image_editor_page.tool_labels["Crop"].text() == "CROP"
    assert window.image_editor_page.tool_labels["Select"].text() == "SELECT"
    assert window.image_editor_page.trim_button.text() == "TRIM"
    assert window.image_editor_page.trim_button.parent() is (
        window.image_editor_page.tool_names_panel
    )
    assert window.image_editor_page.inspector.count() == 2
    assert window.image_editor_page.undo_shortcut.key().toString() == "Ctrl+Z"
    assert window.image_editor_page.redo_shortcut.key().toString() == "Ctrl+Shift+Z"
    assert window.image_editor_page.open_shortcut.key().toString() == "Ctrl+O"
    assert window.image_editor_page.save_shortcut.key().toString() == "Ctrl+S"
    assert window.image_editor_page.trim_shortcut.key().toString() == "Ctrl+T"
    assert window.image_editor_page.crop_shortcut.key().toString() == "C"
    assert window.image_editor_page.select_shortcut.key().toString() == "V"
    assert window.image_editor_page.apply_crop_shortcut.key().toString() == "Return"
    assert window.image_editor_page.apply_crop_numpad_shortcut.key().isEmpty() is False

    window.image_editor_page.tool_labels["Magic Wand"].click()

    assert window.image_editor_page.tool_labels["Magic Wand"].property("active") is True
    assert window.image_editor_page.tool_labels["Background Remover"].property("active") is False

    window.image_editor_page.set_theme_progress(0.0)
    dark_tabs = window.image_editor_page.document_tabs.styleSheet()
    window.image_editor_page.set_theme_progress(1.0)
    light_tabs = window.image_editor_page.document_tabs.styleSheet()

    assert dark_tabs != light_tabs
    assert "#2f3136" in dark_tabs
    assert "#e8eef8" in light_tabs


def test_image_editor_displays_import_at_native_resolution(qtbot, tmp_path) -> None:
    source = tmp_path / "original.png"
    image = QImage(37, 23, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)

    assert page.load_image(source) is True
    assert page.document_tabs.count() == 1
    assert "original.png" in page.document_tabs.tabText(0)

    assert page.canvas_placeholder.pixmap().size().width() == 37
    assert page.canvas_placeholder.pixmap().size().height() == 23
    assert page.canvas_placeholder.size().width() == 37
    assert page.canvas_placeholder.size().height() == 23
    assert page.zoom_percentage.text() == "100%"
    assert page.units_combo.currentData() == "in"
    assert page.width_value.value() > 0
    assert page.height_value.value() > 0

    page.set_zoom(1.25)
    assert page.canvas_placeholder.size().width() == 46
    assert page.canvas_placeholder.size().height() == 29
    assert page.zoom_percentage.text() == "125%"

    page.set_zoom(1.0)
    assert page.canvas_placeholder.size().width() == 37
    assert page.canvas_placeholder.size().height() == 23
    assert page.zoom_percentage.text() == "100%"

    page.set_zoom(0.001)
    assert page._zoom == 0.005
    assert page.zoom_percentage.text() == "0.5%"

    page.set_zoom(1.0)

    page.units_combo.setCurrentIndex(page.units_combo.findData("px"))
    assert page.width_value.value() == 37
    assert page.height_value.value() == 23
    assert page.width_value.suffix() == " px"
    assert page.aspect_lock_button.isChecked() is True
    assert page.canvas_scroll.horizontalScrollBar().maximum() > 0
    assert page.canvas_scroll.verticalScrollBar().maximum() > 0

    page.width_value.setValue(74)
    page.height_value.setValue(46)
    page._resize_from_dimensions()

    assert page._pixmap.width() == 74
    assert page._pixmap.height() == 46
    assert page.canvas_placeholder.width() == 74
    assert page.canvas_placeholder.height() == 46

    page.width_value.setValue(100)
    page._resize_from_dimensions("width")
    assert page._pixmap.width() == 100
    assert page._pixmap.height() == 62

    page.aspect_lock_button.click()
    page.width_value.setValue(80)
    page.height_value.setValue(80)
    page._resize_from_dimensions("width")
    assert page._pixmap.size().width() == 80
    assert page._pixmap.size().height() == 80
    assert page.undo_button.isEnabled() is True

    page.undo_button.click()

    assert page._pixmap.size().width() == 100
    assert page._pixmap.size().height() == 62
    assert page.redo_button.isEnabled() is True

    page.redo_button.click()

    assert page._pixmap.size().width() == 80
    assert page._pixmap.size().height() == 80


def test_image_editor_reuses_an_already_open_design_tab(qtbot, tmp_path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    for path, colour in ((first, "#3366CC"), (second, "#CC6633")):
        image = QImage(20, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor(colour))
        assert image.save(str(path))
    page = ImageEditorPage()
    qtbot.addWidget(page)

    assert page.load_image(first) is True
    assert page.load_image(second) is True
    assert page.document_tabs.count() == 2
    assert page.document_tabs.currentIndex() == 1

    assert page.load_image(first) is True

    assert page.document_tabs.count() == 2
    assert page.document_tabs.currentIndex() == 0
    assert page._image_path == first


def test_image_editor_opens_multiple_images_into_independent_tabs(
    qtbot,
    tmp_path,
) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first_image = QImage(40, 20, QImage.Format.Format_ARGB32)
    second_image = QImage(18, 12, QImage.Format.Format_ARGB32)
    first_image.fill(QColor("#3366CC"))
    second_image.fill(QColor("#CC6633"))
    assert first_image.save(str(first))
    assert second_image.save(str(second))
    page = ImageEditorPage()
    qtbot.addWidget(page)

    assert page.load_image(first) is True
    assert page.load_image(second) is True

    assert page.document_tabs.count() == 2
    assert hasattr(page, "import_button") is False
    assert page.document_tabs.isHidden() is False
    assert page._pixmap.size().width() == 18
    page.set_zoom(1.5)

    page.document_tabs.setCurrentIndex(0)

    assert page._pixmap.size().width() == 40
    assert page.zoom_percentage.text() == "100%"
    assert "first.png" in page.document_tabs.tabText(0)

    page.document_tabs.setCurrentIndex(1)

    assert page._pixmap.size().width() == 18
    assert page.zoom_percentage.text() == "150%"


def test_image_editor_fits_large_image_on_open_without_upscaling(qtbot, tmp_path) -> None:
    source = tmp_path / "large.png"
    image = QImage(2000, 1200, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    page.resize(1100, 700)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)

    assert page.load_image(source) is True

    assert page._zoom < 1.0
    assert page.canvas_placeholder.width() <= page.canvas_scroll.viewport().width()
    assert page.canvas_placeholder.height() <= page.canvas_scroll.viewport().height()


def test_customer_image_dialog_supports_multiple_selection(qtbot) -> None:
    files = [
        SimpleNamespace(
            id=1,
            original_name="one.png",
            local_path="",
            size_bytes=100,
            transfer_state="synced",
        ),
        SimpleNamespace(
            id=2,
            original_name="two.jpg",
            local_path="",
            size_bytes=200,
            transfer_state="synced",
        ),
    ]

    class CustomerService:
        def list_customers(self, *, active=None):
            return [SimpleNamespace(id=7, display_identifier="C007 - Customer")]

        def customer_storage_dates(self, customer_id):
            return ["2026-07-31"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return files

    dialog = CustomerImageDialog(CustomerService(), select_file=True)
    qtbot.addWidget(dialog)
    customer_item = dialog.folder_tree.topLevelItem(0)
    assert customer_item.isExpanded() is False
    assert customer_item.child(0).isExpanded() is False
    dialog.folder_tree.setCurrentItem(customer_item.child(0).child(0))
    dialog.file_table.setRangeSelected(
        QTableWidgetSelectionRange(0, 0, 1, 2),
        True,
    )

    assert dialog.browser_splitter.count() == 3
    assert dialog.folder_tree.topLevelItemCount() == 1
    assert dialog.folder_tree.topLevelItem(0).text(0).startswith("1. ")
    assert dialog.file_table.rowCount() == 2
    assert [record.id for record in dialog.selected_files] == [1, 2]


def test_customer_image_browser_imports_multiple_designs(
    qtbot,
    tmp_path,
    monkeypatch,
) -> None:
    first = tmp_path / "one.png"
    second = tmp_path / "two.png"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    uploaded = []

    class CustomerService:
        def list_customers(self, *, active=None):
            return [SimpleNamespace(id=7, display_identifier="C007 - Customer")]

        def customer_storage_dates(self, customer_id):
            return ["2026-07-31"]

        def list_customer_files(self, customer_id, date_name, folder_name):
            return []

        def upload_customer_file(self, customer_id, date_name, folder_name, source):
            uploaded.append((customer_id, date_name, folder_name, source))

    monkeypatch.setattr(
        "app.ui.pages.image_editor.QFileDialog.getOpenFileNames",
        lambda *args: ([str(first), str(second)], ""),
    )
    dialog = CustomerImageDialog(CustomerService(), select_file=True)
    qtbot.addWidget(dialog)
    customer_item = dialog.folder_tree.topLevelItem(0)
    dialog.folder_tree.setCurrentItem(customer_item.child(0).child(0))

    dialog.import_designs_button.click()

    assert uploaded == [
        (7, "2026-07-31", "Design", first),
        (7, "2026-07-31", "Design", second),
    ]


def test_image_editor_saves_opened_customer_image_to_same_file(
    qtbot,
    tmp_path,
    monkeypatch,
) -> None:
    class CustomerService:
        def __init__(self) -> None:
            self.replacements = []

        def replace_customer_file(self, file_id, source):
            self.replacements.append((file_id, source))

    source = tmp_path / "managed.png"
    image = QImage(37, 23, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    service = CustomerService()
    page = ImageEditorPage(service)
    qtbot.addWidget(page)
    monkeypatch.setattr("app.ui.pages.image_editor.QMessageBox.information", lambda *args: None)
    assert page.load_image(source, source_file_id=42) is True

    page.save_customer_image()

    assert service.replacements == [(42, source)]


def test_order_design_keeps_managed_file_identity_in_editor(qtbot, tmp_path) -> None:
    source = tmp_path / "CR0001 - DE1 - design.png"
    image = QImage(30, 20, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    window = MainWindow()
    qtbot.addWidget(window)

    window._open_designs_in_editor([(source, 41)])

    assert window.router.current_page_name == "image_editor"
    assert window.image_editor_page._source_file_id == 41
    assert window.image_editor_page._image_path == source


def test_image_editor_trims_transparency_and_crop_extends_canvas(
    qtbot,
    tmp_path,
) -> None:
    source = tmp_path / "transparent.png"
    image = QImage(30, 24, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    for y in range(7, 15):
        for x in range(9, 19):
            image.setPixelColor(x, y, QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)
    assert page.load_image(source) is True
    assert page.canvas_workspace.palette().color(QPalette.ColorRole.Window).name() == "#303030"
    assert (
        page.canvas_placeholder.palette().brush(QPalette.ColorRole.Window).texture().isNull()
        is False
    )

    page.trim_transparent_pixels()

    assert page._pixmap.width() == 10
    assert page._pixmap.height() == 8

    page.undo()
    assert page._pixmap.width() == 30
    assert page._pixmap.height() == 24
    page.redo()
    assert page._pixmap.width() == 10
    assert page._pixmap.height() == 8

    page._select_tool("Crop")
    page.aspect_lock_button.setChecked(False)
    page.units_combo.setCurrentIndex(page.units_combo.findData("px"))
    page.width_value.setValue(20)
    page.height_value.setValue(18)
    page._resize_from_dimensions("width")

    assert page._pixmap.width() == 20
    assert page._pixmap.height() == 18
    assert page._pixmap.toImage().pixelColor(0, 0).alpha() == 255


def test_image_editor_interactive_crop_handles_extend_canvas(qtbot, tmp_path) -> None:
    source = tmp_path / "crop-source.png"
    image = QImage(30, 20, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)
    assert page.load_image(source) is True

    page._select_tool("Crop")

    assert page.crop_overlay.isHidden() is False
    assert len(page.crop_overlay._handles()) == 8
    assert page.apply_crop_button.isHidden() is False
    image_geometry = page.canvas_placeholder.geometry()
    page.crop_overlay.crop_rect = QRectF(
        image_geometry.x() - 10,
        image_geometry.y() - 5,
        image_geometry.width() + 20,
        image_geometry.height() + 10,
    )
    crop_before_zoom = QRectF(page.crop_overlay.crop_rect)

    page.set_zoom(2.0)

    assert page.crop_overlay.isHidden() is False
    assert page.crop_overlay.crop_rect.width() == crop_before_zoom.width() * 2
    assert page.crop_overlay.crop_rect.height() == crop_before_zoom.height() * 2

    page.set_zoom(1.0)

    page.apply_interactive_crop()

    assert page._pixmap.width() == 50
    assert page._pixmap.height() == 30
    assert page._pixmap.toImage().pixelColor(0, 0).alpha() == 0
    assert page.crop_overlay.isHidden() is True

    page.undo()

    assert page._pixmap.width() == 30
    assert page._pixmap.height() == 20

    page.start_interactive_crop()
    image_geometry = page.canvas_placeholder.geometry()
    page.crop_overlay.crop_rect = QRectF(
        image_geometry.x() + 5,
        image_geometry.y() + 5,
        image_geometry.width() - 10,
        image_geometry.height() - 10,
    )
    page.apply_interactive_crop()

    assert page._pixmap.width() == 20
    assert page._pixmap.height() == 10


def test_image_editor_select_moves_resizes_and_rotates_artwork(qtbot, tmp_path) -> None:
    source = tmp_path / "select-source.png"
    image = QImage(60, 40, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    for y in range(10, 20):
        for x in range(10, 30):
            image.setPixelColor(x, y, QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)
    assert page.load_image(source) is True
    page.units_combo.setCurrentIndex(page.units_combo.findData("px"))

    page.width_value.setValue(30)
    assert page.height_value.value() == 20
    page.width_value.setValue(60)
    assert page.height_value.value() == 40

    original_size = page._pixmap.size()
    page.resolution_value.setValue(300)
    page._change_resolution()
    assert page._pixmap.size() == original_size
    assert "@ 300 DPI" in page.image_info.text()
    saved = QImage(str(page._edited_source()))
    assert round(saved.dotsPerMeterX() * 0.0254) == 300

    page._select_tool("Select")

    assert page.selection_overlay.isHidden() is False
    assert page.width_value.value() == 60
    assert page.height_value.value() == 40
    assert page.rotation_value.isEnabled() is True

    page._move_selected_artwork(QPoint(10, 5))
    moved_bounds = page._visible_pixel_bounds()
    assert moved_bounds.x() == 20
    assert moved_bounds.y() == 15

    page._position_selection_overlay()
    start = page.selection_overlay.geometry()
    assert (
        page.selection_overlay._hit_test(page.selection_overlay.rect().bottomRight())
        == "bottom_right"
    )
    resized = QRect(start)
    resized.setRight(start.right() + start.width())
    resized.setBottom(start.bottom() + start.height())
    page._selection_transform_completed(start, resized)
    handle_resized_bounds = page._visible_pixel_bounds()
    assert handle_resized_bounds.width() == 40
    assert handle_resized_bounds.height() == 20

    page.width_value.setValue(120)
    page._resize_from_dimensions("width")
    assert page._pixmap.size() == QSize(120, 80)
    assert page.selection_overlay.isHidden() is True

    page.rotation_value.setValue(90)
    page._rotate_image()
    assert page._pixmap.size() == QSize(80, 120)
    assert page.rotation_value.value() == 90

    page.rotation_value.setValue(45)
    page._rotate_image()
    assert page.rotation_value.value() == 45
    page.undo()
    assert page.rotation_value.value() == 90
    page.redo()
    assert page.rotation_value.value() == 45
    assert page.undo_button.isEnabled() is True


def test_image_editor_top_dimensions_resize_image_even_when_crop_is_active(qtbot, tmp_path) -> None:
    source = tmp_path / "crop-active-resize.png"
    image = QImage(60, 40, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)
    assert page.load_image(source) is True
    page.units_combo.setCurrentIndex(page.units_combo.findData("px"))
    page._select_tool("Crop")
    page.show()
    page.canvas_scroll.setFocus()
    qtbot.keyClick(page.canvas_scroll, Qt.Key.Key_V)
    assert page._active_tool == "Select"
    assert page.selection_overlay.isHidden() is False

    start = page.selection_overlay.geometry()
    moved = start.translated(20, 10)
    page._selection_transform_completed(start, moved, "move")
    assert page.selection_overlay.geometry().center() == moved.center()

    start = page.selection_overlay.geometry()
    enlarged = QRect(start)
    enlarged.setRight(start.right() + start.width())
    enlarged.setBottom(start.bottom() + start.height())
    page._selection_transform_completed(start, enlarged, "bottom_right")
    assert page._selection_width == 120
    assert page._selection_height == 80

    page.undo()
    page.undo()
    page._select_tool("Crop")

    page.width_value.setValue(120)
    assert page.height_value.value() == 80
    page._resize_from_dimensions("width")

    assert page._pixmap.size() == QSize(120, 80)
    assert page._visible_pixel_bounds() == QRect(0, 0, 120, 80)
    assert page.crop_overlay.isHidden() is True

    page._select_tool("Select")
    qtbot.mouseClick(page.canvas_scroll.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
    assert page._active_tool == ""
    assert page.selection_overlay.isHidden() is True
    assert all(not button.isChecked() for button in page.tool_labels.values())


def test_image_editor_round_eraser_has_adjustable_size_and_undo(qtbot, tmp_path) -> None:
    source = tmp_path / "eraser-source.png"
    image = QImage(60, 40, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)
    assert page.load_image(source) is True

    page._select_tool("Eraser")
    assert page.eraser_controls.isHidden() is False
    page.eraser_size_slider.setValue(12)
    assert page.eraser_size_value.value() == 12

    page._push_undo()
    page._erase_segment(QPoint(20, 20), QPoint(40, 20))
    erased = page._pixmap.toImage()
    assert erased.pixelColor(30, 20).alpha() == 0
    assert erased.pixelColor(0, 0).alpha() == 255

    page.undo()
    assert page._pixmap.toImage().pixelColor(30, 20).alpha() == 255


def test_image_editor_magic_eraser_removes_matching_colour_with_tolerance(qtbot, tmp_path) -> None:
    source = tmp_path / "magic-eraser-source.png"
    image = QImage(20, 10, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    for y in range(10):
        for x in range(8, 12):
            image.setPixelColor(x, y, QColor("#CC3333"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)
    assert page.load_image(source) is True

    page._select_tool("Magic Eraser")
    assert page.magic_eraser_controls.isHidden() is False
    page.magic_eraser_tolerance_slider.setValue(10)
    assert page.magic_eraser_tolerance_value.value() == 10
    assert page.magic_eraser_contiguous.isChecked() is True
    assert page.magic_eraser_contiguous.text() == "Contiguous: ON"

    page._push_undo()
    page._magic_erase_at(QPoint(2, 2))
    erased = page._pixmap.toImage()
    assert erased.pixelColor(2, 2).alpha() == 0
    assert erased.pixelColor(9, 2).alpha() == 255
    assert erased.pixelColor(15, 2).alpha() == 255

    page.undo()
    assert page._pixmap.toImage().pixelColor(2, 2).alpha() == 255

    qtbot.mouseClick(page.magic_eraser_contiguous, Qt.MouseButton.LeftButton)
    assert page.magic_eraser_contiguous.isChecked() is False
    assert page.magic_eraser_contiguous.text() == "Contiguous: OFF"
    page._push_undo()
    page._magic_erase_at(QPoint(2, 2))
    erased = page._pixmap.toImage()
    assert erased.pixelColor(2, 2).alpha() == 0
    assert erased.pixelColor(15, 2).alpha() == 0
    assert erased.pixelColor(9, 2).alpha() == 255
