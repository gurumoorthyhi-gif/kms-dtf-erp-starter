from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from app.ui.application import MainWindow, PageRouter
from app.ui.components import (
    ANIMATION_DURATION_MS,
    COLLAPSED_WIDTH,
    EXPANDED_WIDTH,
    Sidebar,
)
from app.ui.icons import create_navigation_icon
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

    qtbot.mouseClick(sidebar._toggle_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: sidebar.width() == EXPANDED_WIDTH, timeout=1000)

    assert sidebar.is_expanded is True
    assert sidebar.button_for("dashboard").text() == "Dashboard"
    assert sidebar.button_for("dashboard").toolTip() == ""

    qtbot.mouseClick(sidebar._toggle_button, Qt.MouseButton.LeftButton)
    # Keep expanded alignment until the width animation completes; switching
    # immediately makes the icon jump across the still-wide sidebar.
    assert sidebar.button_for("dashboard").text() == "Dashboard"
    qtbot.waitUntil(lambda: sidebar.width() == COLLAPSED_WIDTH, timeout=1000)
    qtbot.waitUntil(
        lambda: sidebar.button_for("dashboard").text() == "",
        timeout=1000,
    )

    assert sidebar.is_expanded is False
    assert sidebar.button_for("dashboard").text() == ""
    assert sidebar.button_for("dashboard").toolTip() == "Dashboard"
    assert sidebar.button_for("dashboard").property("expanded") is False


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


def test_navigation_uses_supplied_icon_assets() -> None:
    assert create_navigation_icon("dashboard").isNull() is False
    assert create_navigation_icon("studio").isNull() is False
    asset = (
        Path(__file__).resolve().parents[2] / "assets" / "icons" / "navigation" / "dashboard.png"
    )
    image = QImage(str(asset))
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0


def test_main_window_scales_shell_at_small_sizes(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    window.resize(860, 560)
    qtbot.waitUntil(lambda: window.sidebar.is_compact)
    assert window.sidebar.button_for("dashboard").iconSize().width() == 34

    window.resize(1280, 800)
    qtbot.waitUntil(lambda: not window.sidebar.is_compact)
    assert window.sidebar.button_for("dashboard").iconSize().width() == 38
