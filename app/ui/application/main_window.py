"""Main application shell."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.modules.authentication import AuthenticatedUser, AuthenticationService
from app.modules.customers import CustomerService
from app.modules.dashboard import DashboardService
from app.ui.application.router import PageRouter
from app.ui.components import Sidebar, TopBar
from app.ui.pages import CustomersPage, DashboardPage, LoginPage, SettingsPage
from app.ui.themes import APP_STYLESHEET


class MainWindow(QMainWindow):
    """Presentation-only Phase 3 shell."""

    PAGE_CONTEXT = {
        "dashboard": ("Dashboard", "Workspace overview"),
        "customers": ("Customers", "Customer records and contacts"),
        "settings": ("Settings", "Application preferences"),
    }

    def __init__(
        self,
        authentication_service: AuthenticationService | None = None,
        dashboard_service: DashboardService | None = None,
        customer_service: CustomerService | None = None,
    ) -> None:
        super().__init__()
        self._authentication_service = authentication_service
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
        self.dashboard_page = DashboardPage(
            dashboard_service,
            auto_refresh=authentication_service is None,
        )
        self.dashboard_page.navigation_requested.connect(self.navigate)
        self.router.register_page("dashboard", self.dashboard_page)
        self.customers_page: CustomersPage | None = None
        if customer_service is not None:
            self.customers_page = CustomersPage(customer_service, auto_refresh=False)
            self.router.register_page("customers", self.customers_page)
        self.router.register_page("settings", SettingsPage())
        self.sidebar.set_page_visible("customers", customer_service is not None)
        self.login_page: LoginPage | None = None
        if authentication_service is not None:
            self.login_page = LoginPage(authentication_service)
            self.router.register_page("login", self.login_page)
            self.login_page.login_succeeded.connect(self._complete_login)

        workspace = QVBoxLayout()
        workspace.setSpacing(18)
        workspace.addWidget(self.top_bar)
        workspace.addWidget(self.router, 1)

        shell_layout.addWidget(self.sidebar)
        shell_layout.addLayout(workspace, 1)
        self.setCentralWidget(root)

        self.sidebar.navigation_requested.connect(self.navigate)
        self.top_bar.logout_requested.connect(self.logout)
        if authentication_service is None:
            self.navigate("dashboard")
        else:
            self._show_login()

    def navigate(self, page_name: str) -> None:
        """Switch shell pages and synchronize the navigation context."""

        title, subtitle = self.PAGE_CONTEXT[page_name]
        self.router.navigate(page_name)
        self.sidebar.set_active_page(page_name)
        self.top_bar.set_page_context(title, subtitle)

    def _show_login(self) -> None:
        self.sidebar.setVisible(False)
        self.top_bar.setVisible(False)
        if self.login_page is not None:
            self.login_page.reset()
        self.router.navigate("login")

    def _complete_login(self, user: AuthenticatedUser) -> None:
        self.sidebar.setVisible(True)
        self.top_bar.setVisible(True)
        self.top_bar.set_authenticated_user(user.full_name)
        self.dashboard_page.refresh()
        if self.customers_page is not None:
            can_view_customers = "customers.view" in user.permissions
            self.sidebar.set_page_visible("customers", can_view_customers)
            if can_view_customers:
                self.customers_page.refresh()
        self.navigate("dashboard")

    def logout(self) -> None:
        """End the service session and return to the login page."""

        if self._authentication_service is None:
            return
        self._authentication_service.logout()
        self.top_bar.set_authenticated_user(None)
        self._show_login()
