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


def test_sidebar_expands_and_collapses(qtbot) -> None:
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.show()

    assert sidebar.width() == COLLAPSED_WIDTH
    assert sidebar.animation_duration == ANIMATION_DURATION_MS == 240
    assert sidebar.button_for("dashboard").text() == ""
    assert sidebar.button_for("dashboard").toolTip() == "Dashboard"

    sidebar.expand()
    qtbot.waitUntil(lambda: sidebar.width() == EXPANDED_WIDTH, timeout=1000)

    assert sidebar.is_expanded is True
    assert sidebar.button_for("dashboard").text() == "Dashboard"
    assert sidebar.button_for("dashboard").toolTip() == ""

    sidebar.collapse()
    qtbot.waitUntil(lambda: sidebar.width() == COLLAPSED_WIDTH, timeout=1000)

    assert sidebar.is_expanded is False
    assert sidebar.button_for("dashboard").text() == ""
    assert sidebar.button_for("dashboard").toolTip() == "Dashboard"


def test_main_window_routes_placeholder_pages(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.router.current_page_name == "dashboard"
    assert window.top_bar.title == "Dashboard"
    assert window.sidebar.button_for("dashboard").property("active") is True

    window.navigate("settings")

    assert window.router.current_page_name == "settings"
    assert window.top_bar.title == "Settings"
    assert window.sidebar.button_for("settings").property("active") is True
