from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QImage, QPalette

from app.ui.application import MainWindow, PageRouter
from app.ui.components import (
    ANIMATION_DURATION_MS,
    COLLAPSED_WIDTH,
    EXPANDED_WIDTH,
    Sidebar,
)
from app.ui.pages import DashboardPage, ImageEditorPage


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
    assert len(window.image_editor_page.tool_labels) == 10
    assert (
        window.image_editor_page.tool_labels["Background Remover"].property("active")
        is True
    )
    assert window.image_editor_page.tool_labels["Background Remover"].text() == (
        "BACKGROUND REMOVER"
    )
    assert window.image_editor_page.tool_labels["Trace Bitmap"].text() == "TRACE BITMAP"
    assert window.image_editor_page.tool_labels["Crop"].text() == "CROP"
    assert window.image_editor_page.inspector.count() == 2

    window.image_editor_page.tool_labels["Magic Wand"].click()

    assert window.image_editor_page.tool_labels["Magic Wand"].property("active") is True
    assert (
        window.image_editor_page.tool_labels["Background Remover"].property("active")
        is False
    )


def test_image_editor_displays_import_at_native_resolution(qtbot, tmp_path) -> None:
    source = tmp_path / "original.png"
    image = QImage(37, 23, QImage.Format.Format_ARGB32)
    image.fill(QColor("#3366CC"))
    assert image.save(str(source))
    page = ImageEditorPage()
    qtbot.addWidget(page)

    assert page.load_image(source) is True

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
    assert (
        page.canvas_workspace.palette().color(QPalette.ColorRole.Window).name()
        == "#303030"
    )
    assert (
        page.canvas_placeholder.palette()
        .brush(QPalette.ColorRole.Window)
        .texture()
        .isNull()
        is False
    )

    page.trim_transparent_pixels()

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
    assert page._pixmap.toImage().pixelColor(0, 0).alpha() == 0
