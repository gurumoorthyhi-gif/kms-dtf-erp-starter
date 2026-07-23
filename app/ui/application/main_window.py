"""Main application shell."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.modules.ai_engine import AIJobManager
from app.modules.artwork import ArtworkService
from app.modules.artwork_studio import ArtworkStudioService
from app.modules.authentication import AuthenticatedUser, AuthenticationService
from app.modules.customers import CustomerService
from app.modules.dashboard import DashboardService
from app.modules.gang_sheets import GangSheetService
from app.modules.orders import OrderService
from app.modules.production import ProductionService
from app.modules.products import ProductService
from app.ui.application.router import PageRouter
from app.ui.components import Sidebar, TopBar
from app.ui.pages import (
    AIToolsPage,
    ArtworkLibraryPage,
    ArtworkStudioPage,
    CustomersPage,
    DashboardPage,
    GangSheetPage,
    LoginPage,
    OrdersPage,
    ProductionPage,
    ProductsPage,
    SettingsPage,
)
from app.ui.themes import APP_STYLESHEET


class MainWindow(QMainWindow):
    """Presentation-only Phase 3 shell."""

    PAGE_CONTEXT = {
        "dashboard": ("Dashboard", "Workspace overview"),
        "customers": ("Customers", "Customer records and contacts"),
        "products": ("Products", "Products and pricing rules"),
        "orders": ("Orders", "Order workflow and production status"),
        "artwork": ("Artwork", "Artwork library, versions, and approvals"),
        "studio": ("Artwork Studio", "Local non-destructive image tools"),
        "ai_tools": ("AI Tools", "Separate AI image engine jobs"),
        "gang_sheets": ("Gang Sheets", "Artwork nesting and original-quality export"),
        "production": ("Production", "Production queue, stages, and quality"),
        "settings": ("Settings", "Application preferences"),
    }

    def __init__(
        self,
        authentication_service: AuthenticationService | None = None,
        dashboard_service: DashboardService | None = None,
        customer_service: CustomerService | None = None,
        product_service: ProductService | None = None,
        order_service: OrderService | None = None,
        artwork_service: ArtworkService | None = None,
        artwork_studio_service: ArtworkStudioService | None = None,
        ai_job_manager: AIJobManager | None = None,
        gang_sheet_service: GangSheetService | None = None,
        production_service: ProductionService | None = None,
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
        self.products_page: ProductsPage | None = None
        if product_service is not None:
            self.products_page = ProductsPage(product_service, auto_refresh=False)
            self.router.register_page("products", self.products_page)
        self.sidebar.set_page_visible("products", product_service is not None)
        self.orders_page: OrdersPage | None = None
        if (
            order_service is not None
            and customer_service is not None
            and product_service is not None
        ):
            self.orders_page = OrdersPage(
                order_service,
                customer_service,
                product_service,
                auto_refresh=False,
            )
            self.router.register_page("orders", self.orders_page)
        self.sidebar.set_page_visible("orders", self.orders_page is not None)
        self.artwork_page: ArtworkLibraryPage | None = None
        if (
            artwork_service is not None
            and customer_service is not None
            and order_service is not None
        ):
            self.artwork_page = ArtworkLibraryPage(
                artwork_service,
                customer_service,
                order_service,
                auto_refresh=False,
            )
            self.router.register_page("artwork", self.artwork_page)
        self.sidebar.set_page_visible("artwork", self.artwork_page is not None)
        self.studio_page: ArtworkStudioPage | None = None
        if artwork_service is not None and artwork_studio_service is not None:
            self.studio_page = ArtworkStudioPage(
                artwork_studio_service,
                artwork_service,
                auto_refresh=False,
            )
            self.router.register_page("studio", self.studio_page)
        self.sidebar.set_page_visible("studio", self.studio_page is not None)
        self.ai_tools_page: AIToolsPage | None = None
        if artwork_service is not None and ai_job_manager is not None:
            self.ai_tools_page = AIToolsPage(
                ai_job_manager,
                artwork_service,
                auto_refresh=False,
            )
            self.router.register_page("ai_tools", self.ai_tools_page)
        self.sidebar.set_page_visible("ai_tools", self.ai_tools_page is not None)
        self.gang_sheet_page: GangSheetPage | None = None
        if artwork_service is not None and gang_sheet_service is not None:
            self.gang_sheet_page = GangSheetPage(
                gang_sheet_service,
                artwork_service,
                auto_refresh=False,
            )
            self.router.register_page("gang_sheets", self.gang_sheet_page)
        self.sidebar.set_page_visible("gang_sheets", self.gang_sheet_page is not None)
        self.production_page: ProductionPage | None = None
        if production_service is not None and order_service is not None:
            self.production_page = ProductionPage(
                production_service,
                order_service,
                auto_refresh=False,
            )
            self.router.register_page("production", self.production_page)
        self.sidebar.set_page_visible("production", self.production_page is not None)
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
        if self.products_page is not None:
            can_view_products = "products.view" in user.permissions
            self.sidebar.set_page_visible("products", can_view_products)
            if can_view_products:
                self.products_page.refresh()
        if self.orders_page is not None:
            can_view_orders = "orders.view" in user.permissions
            self.sidebar.set_page_visible("orders", can_view_orders)
            if can_view_orders:
                self.orders_page.refresh()
        if self.artwork_page is not None:
            can_view_artwork = "artwork.view" in user.permissions
            self.sidebar.set_page_visible("artwork", can_view_artwork)
            if can_view_artwork:
                self.artwork_page.refresh()
        if self.studio_page is not None:
            can_use_studio = "artwork.manage" in user.permissions
            self.sidebar.set_page_visible("studio", can_use_studio)
            if can_use_studio:
                self.studio_page.refresh()
        if self.ai_tools_page is not None:
            can_use_ai = "ai.use" in user.permissions
            self.sidebar.set_page_visible("ai_tools", can_use_ai)
            if can_use_ai:
                self.ai_tools_page.refresh()
        if self.gang_sheet_page is not None:
            can_view_gang_sheets = "gang_sheets.view" in user.permissions
            self.sidebar.set_page_visible("gang_sheets", can_view_gang_sheets)
            if can_view_gang_sheets:
                self.gang_sheet_page.refresh()
        if self.production_page is not None:
            can_view_production = "production.view" in user.permissions
            self.sidebar.set_page_visible("production", can_view_production)
            if can_view_production:
                self.production_page.refresh()
        self.navigate("dashboard")

    def logout(self) -> None:
        """End the service session and return to the login page."""

        if self._authentication_service is None:
            return
        self._authentication_service.logout()
        self.top_bar.set_authenticated_user(None)
        self._show_login()
