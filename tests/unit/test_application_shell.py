from PySide6.QtCore import QSettings

from app.ui.application import MainWindow, PageRouter
from app.ui.components import (
    ANIMATION_DURATION_MS,
    COLLAPSED_WIDTH,
    EXPANDED_WIDTH,
    Sidebar,
)
from app.ui.pages import DashboardPage


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
