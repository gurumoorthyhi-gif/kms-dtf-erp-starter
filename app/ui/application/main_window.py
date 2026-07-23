"""Main application shell."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.ui.application.router import PageRouter
from app.ui.components import Sidebar, TopBar
from app.ui.pages import DashboardPage, SettingsPage
from app.ui.themes import APP_STYLESHEET


class MainWindow(QMainWindow):
    """Presentation-only Phase 3 shell."""

    PAGE_CONTEXT = {
        "dashboard": ("Dashboard", "Workspace overview"),
        "settings": ("Settings", "Application preferences"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("KMS DTF ERP")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(APP_STYLESHEET)

        root = QWidget()
        root.setObjectName("applicationRoot")
        shell_layout = QHBoxLayout(root)
        shell_layout.setContentsMargins(16, 16, 16, 16)
        shell_layout.setSpacing(18)

        self.sidebar = Sidebar()
        self.top_bar = TopBar()
        self.router = PageRouter()
        self.router.register_page("dashboard", DashboardPage())
        self.router.register_page("settings", SettingsPage())

        workspace = QVBoxLayout()
        workspace.setSpacing(18)
        workspace.addWidget(self.top_bar)
        workspace.addWidget(self.router, 1)

        shell_layout.addWidget(self.sidebar)
        shell_layout.addLayout(workspace, 1)
        self.setCentralWidget(root)

        self.sidebar.navigation_requested.connect(self.navigate)
        self.navigate("dashboard")

    def navigate(self, page_name: str) -> None:
        """Switch shell pages and synchronize the navigation context."""

        title, subtitle = self.PAGE_CONTEXT[page_name]
        self.router.navigate(page_name)
        self.sidebar.set_active_page(page_name)
        self.top_bar.set_page_context(title, subtitle)
