"""Main application shell."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QSettings, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.modules.ai_engine import AIJobManager
from app.modules.artwork import ArtworkService
from app.modules.authentication import AuthenticatedUser, AuthenticationService
from app.modules.cloud_storage import CloudStorageService, StorageConfigurationStore
from app.modules.communications import CommunicationService
from app.modules.customers import CustomerService
from app.modules.dashboard import DashboardService
from app.modules.gang_sheets import GangSheetService
from app.modules.inventory import InventoryService, PurchaseService
from app.modules.operations import AuditService, BackupService, ReportService
from app.modules.orders import OrderService
from app.modules.products import ProductService
from app.modules.sales import SalesService
from app.modules.shipping import DispatchService, PackingService
from app.ui.application.router import PageRouter
from app.ui.branding import application_icon
from app.ui.components import GlassApplicationBackground, Sidebar, TopBar
from app.ui.pages import (
    AIToolsPage,
    ArtworkLibraryPage,
    ArtworkStudioPage,
    CloudStoragePage,
    CustomersPage,
    DashboardPage,
    DispatchPage,
    EmailInboxPage,
    InventoryPage,
    InvoicesPage,
    LoginPage,
    OperationsPage,
    OrdersPage,
    PackingPage,
    PaymentsPage,
    ProductsPage,
    PurchasesPage,
    SalesPage,
    SettingsPage,
    SuppliersPage,
    WhatsAppInboxPage,
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
        "studio": ("Artwork Studio", "DTF gangsheet design and production export"),
        "ai_tools": ("AI Tools", "Separate AI image engine jobs"),
        "inventory": ("Inventory", "Stock levels, movements, and reorder warnings"),
        "suppliers": ("Suppliers", "Supplier directory and purchasing contacts"),
        "purchases": ("Purchases", "Purchase orders and stock receipts"),
        "sales": ("Sales", "Quotations and conversion workflow"),
        "invoices": ("Invoices", "Customer invoices and PDF export"),
        "payments": ("Payments", "Advances, receipts, credits, and balances"),
        "packing": ("Packing", "Packing lists, package counts, and weights"),
        "dispatch": ("Dispatch", "Couriers, tracking, labels, and delivery"),
        "cloud_storage": ("Cloud Storage", "Offline queue, transfers, and synchronization"),
        "whatsapp": ("WhatsApp", "Shared customer conversation inbox"),
        "email": ("Email", "Customer email inbox and history"),
        "operations": ("Reports & Backup", "Reports, verified backup, restore, and audit"),
        "settings": ("Settings", "Application preferences"),
    }

    def get_theme_progress(self) -> float:
        return getattr(self, "_theme_progress", 0.0)

    def set_theme_progress(self, value: float) -> None:
        self._theme_progress = value
        if hasattr(self, "_background"):
            self._background.set_theme_progress(value)
        self.setStyleSheet(APP_STYLESHEET + self._theme_overlay(value))

    themeProgress = Property(float, get_theme_progress, set_theme_progress)

    @staticmethod
    def _theme_overlay(progress: float) -> str:
        def mix(dark: tuple[int, int, int], light: tuple[int, int, int]) -> str:
            values = [
                round(start + ((end - start) * progress))
                for start, end in zip(dark, light, strict=True)
            ]
            return f"rgb({values[0]}, {values[1]}, {values[2]})"

        surface = mix((30, 43, 82), (247, 250, 255))
        surface_soft = mix((39, 54, 99), (231, 239, 252))
        border = mix((73, 91, 145), (188, 205, 232))
        primary = mix((238, 244, 255), (29, 43, 76))
        secondary = mix((179, 194, 224), (92, 108, 143))
        return f"""
        QFrame#topBar, QFrame#glassCard, QFrame#loginCard,
        QFrame#dashboardFilterBar, QFrame#kpiCard, QFrame#dashboardPanel,
        QFrame#customerToolbar, QTableWidget#customerTable {{
            background: {surface};
            border: 1px solid {border};
        }}
        QFrame#pipelineStage, QFrame#activityRow {{
            background: {surface_soft};
            border-color: {border};
        }}
        QLabel#pageTitle, QLabel#cardTitle, QLabel#kpiValue,
        QLabel#filterLabel, QLabel#panelTitle, QLabel#detailsTitle,
        QLabel#activityAction {{
            color: {primary};
        }}
        QLabel#pageSubtitle, QLabel#cardBody, QLabel#kpiLabel,
        QLabel#stageName, QLabel#activityDetail, QLabel#emptyState {{
            color: {secondary};
        }}
        """

    def __init__(
        self,
        authentication_service: AuthenticationService | None = None,
        dashboard_service: DashboardService | None = None,
        initial_user: AuthenticatedUser | None = None,
        customer_service: CustomerService | None = None,
        product_service: ProductService | None = None,
        order_service: OrderService | None = None,
        artwork_service: ArtworkService | None = None,
        ai_job_manager: AIJobManager | None = None,
        gang_sheet_service: GangSheetService | None = None,
        inventory_service: InventoryService | None = None,
        purchase_service: PurchaseService | None = None,
        sales_service: SalesService | None = None,
        packing_service: PackingService | None = None,
        dispatch_service: DispatchService | None = None,
        cloud_storage_service: CloudStorageService | None = None,
        whatsapp_service: CommunicationService | None = None,
        email_service: CommunicationService | None = None,
        report_service: ReportService | None = None,
        backup_service: BackupService | None = None,
        audit_service: AuditService | None = None,
        storage_configuration_store: StorageConfigurationStore | None = None,
        google_sync=None,
    ) -> None:
        super().__init__()
        selected_theme = QSettings("KMS", "DTF ERP").value("ui/theme", "dark")
        self._theme_progress = 0.0 if selected_theme == "dark" else 1.0
        self._theme_animation = QPropertyAnimation(self, b"themeProgress", self)
        self._theme_animation.setDuration(350)
        self._theme_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._authentication_service = authentication_service
        self._customer_service = customer_service
        self._cloud_storage_service = cloud_storage_service
        self.setWindowTitle("KMS DTF ERP")
        self.setWindowIcon(application_icon())
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.set_theme_progress(self._theme_progress)

        root = GlassApplicationBackground()
        self._background = root
        root.set_theme_progress(self._theme_progress)
        root.setObjectName("applicationRoot")
        shell_layout = QHBoxLayout(root)
        shell_layout.setContentsMargins(16, 16, 16, 16)
        shell_layout.setSpacing(18)

        self.sidebar = Sidebar()
        self.sidebar.theme_changed.connect(self._animate_theme)
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
        self.router.register_page(
            "settings",
            SettingsPage(
                cloud_storage_service,
                storage_configuration_store,
                google_sync,
            ),
        )
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
        self.ai_tools_page: AIToolsPage | None = None
        if artwork_service is not None and ai_job_manager is not None:
            self.ai_tools_page = AIToolsPage(
                ai_job_manager,
                artwork_service,
                auto_refresh=False,
            )
            self.router.register_page("ai_tools", self.ai_tools_page)
        self.sidebar.set_page_visible("ai_tools", self.ai_tools_page is not None)
        self.studio_page: ArtworkStudioPage | None = None
        if artwork_service is not None and gang_sheet_service is not None:
            self.studio_page = ArtworkStudioPage(
                gang_sheet_service,
                artwork_service,
                auto_refresh=False,
            )
            self.router.register_page("studio", self.studio_page)
        self.sidebar.set_page_visible("studio", self.studio_page is not None)
        self.inventory_page: InventoryPage | None = None
        if inventory_service is not None:
            self.inventory_page = InventoryPage(inventory_service, auto_refresh=False)
            self.router.register_page("inventory", self.inventory_page)
        self.sidebar.set_page_visible("inventory", self.inventory_page is not None)
        self.suppliers_page: SuppliersPage | None = None
        if purchase_service is not None:
            self.suppliers_page = SuppliersPage(purchase_service, auto_refresh=False)
            self.router.register_page("suppliers", self.suppliers_page)
        self.sidebar.set_page_visible("suppliers", self.suppliers_page is not None)
        self.purchases_page: PurchasesPage | None = None
        if purchase_service is not None and inventory_service is not None:
            self.purchases_page = PurchasesPage(
                purchase_service,
                inventory_service,
                auto_refresh=False,
            )
            self.router.register_page("purchases", self.purchases_page)
        self.sidebar.set_page_visible("purchases", self.purchases_page is not None)
        self.sales_page: SalesPage | None = None
        self.invoices_page: InvoicesPage | None = None
        if sales_service is not None and order_service is not None:
            self.sales_page = SalesPage(sales_service, order_service, auto_refresh=False)
            self.invoices_page = InvoicesPage(sales_service, order_service, auto_refresh=False)
            self.router.register_page("sales", self.sales_page)
            self.router.register_page("invoices", self.invoices_page)
        self.sidebar.set_page_visible("sales", self.sales_page is not None)
        self.sidebar.set_page_visible("invoices", self.invoices_page is not None)
        self.payments_page: PaymentsPage | None = None
        if sales_service is not None:
            self.payments_page = PaymentsPage(sales_service, auto_refresh=False)
            self.router.register_page("payments", self.payments_page)
        self.sidebar.set_page_visible("payments", self.payments_page is not None)
        self.packing_page: PackingPage | None = None
        if packing_service is not None and order_service is not None:
            self.packing_page = PackingPage(packing_service, order_service, auto_refresh=False)
            self.router.register_page("packing", self.packing_page)
        self.sidebar.set_page_visible("packing", self.packing_page is not None)
        self.dispatch_page: DispatchPage | None = None
        if dispatch_service is not None and packing_service is not None:
            self.dispatch_page = DispatchPage(dispatch_service, packing_service, auto_refresh=False)
            self.router.register_page("dispatch", self.dispatch_page)
        self.sidebar.set_page_visible("dispatch", self.dispatch_page is not None)
        self.cloud_storage_page: CloudStoragePage | None = None
        if cloud_storage_service is not None:
            self.cloud_storage_page = CloudStoragePage(cloud_storage_service, auto_refresh=False)
            self.router.register_page("cloud_storage", self.cloud_storage_page)
        self.sidebar.set_page_visible("cloud_storage", self.cloud_storage_page is not None)
        self.whatsapp_page: WhatsAppInboxPage | None = None
        if whatsapp_service is not None:
            self.whatsapp_page = WhatsAppInboxPage(whatsapp_service, auto_refresh=False)
            self.router.register_page("whatsapp", self.whatsapp_page)
        self.sidebar.set_page_visible("whatsapp", self.whatsapp_page is not None)
        self.email_page: EmailInboxPage | None = None
        if email_service is not None:
            self.email_page = EmailInboxPage(email_service, auto_refresh=False)
            self.router.register_page("email", self.email_page)
        self.sidebar.set_page_visible("email", self.email_page is not None)
        self.operations_page: OperationsPage | None = None
        if report_service and backup_service and audit_service:
            self.operations_page = OperationsPage(report_service, backup_service, audit_service)
            self.router.register_page("operations", self.operations_page)
        self.sidebar.set_page_visible("operations", self.operations_page is not None)
        self.login_page: LoginPage | None = None
        if authentication_service is not None:
            self.login_page = LoginPage(authentication_service)
            self.router.register_page("login", self.login_page)
            self.login_page.login_succeeded.connect(self._complete_login)

        workspace = QVBoxLayout()
        workspace.setSpacing(18)
        workspace.addWidget(self.top_bar)
        workspace.addWidget(self.router, 1)
        drive_footer = QHBoxLayout()
        drive_footer.addStretch()
        self.google_drive_button = QPushButton()
        self.google_drive_button.setObjectName("secondaryButton")
        self.google_drive_button.setVisible(
            customer_service is not None and customer_service.google_drive_available
        )
        self.google_drive_button.clicked.connect(self._open_google_drive)
        drive_footer.addWidget(self.google_drive_button)
        workspace.addLayout(drive_footer)
        self._update_google_drive_button()

        shell_layout.addWidget(self.sidebar)
        shell_layout.addLayout(workspace, 1)
        self.setCentralWidget(root)

        self.sidebar.navigation_requested.connect(self.navigate)
        self.top_bar.logout_requested.connect(self.logout)
        if initial_user is not None:
            self._complete_login(initial_user)
        elif authentication_service is None:
            self.navigate("dashboard")
        else:
            self._show_login()

    def _animate_theme(self, dark_mode: bool) -> None:
        self._theme_animation.stop()
        self._theme_animation.setStartValue(self._theme_progress)
        self._theme_animation.setEndValue(0.0 if dark_mode else 1.0)
        self._theme_animation.start()

    def _update_google_drive_button(self) -> None:
        connected = bool(
            self._customer_service is not None and self._customer_service.google_drive_connected
        )
        self.google_drive_button.setText(
            "Open Google Drive" if connected else "Connect Google Drive"
        )
        self.google_drive_button.setToolTip(
            "Open the universal DTF ERP Drive folder"
            if connected
            else "Connect Google Drive for universal ERP synchronization"
        )

    def _open_google_drive(self) -> None:
        if self._customer_service is None:
            return
        if self._customer_service.google_drive_connected:
            url = self._customer_service.google_drive_url
            if url:
                QDesktopServices.openUrl(QUrl(url))
            return
        self.google_drive_button.setEnabled(False)
        self.google_drive_button.setText("Connecting...")
        try:
            url = self._customer_service.connect_google_drive()
            if url:
                QDesktopServices.openUrl(QUrl(url))
        except Exception as error:
            QMessageBox.warning(self, "Google Drive not connected", str(error))
        else:
            if self._cloud_storage_service is not None:
                self._cloud_storage_service.set_upload_completed_callback(
                    self._customer_service.create_google_storage_catalog_entry
                )
            QMessageBox.information(
                self,
                "Google Drive connected",
                "The universal ERP folders and Customer Master Sheet are ready.",
            )
        finally:
            self.google_drive_button.setEnabled(True)
            self._update_google_drive_button()

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
        if self.ai_tools_page is not None:
            can_use_ai = "ai.use" in user.permissions
            self.sidebar.set_page_visible("ai_tools", can_use_ai)
            if can_use_ai:
                self.ai_tools_page.refresh()
        if self.studio_page is not None:
            can_view_gang_sheets = "gang_sheets.view" in user.permissions
            self.sidebar.set_page_visible("studio", can_view_gang_sheets)
            if can_view_gang_sheets:
                self.studio_page.refresh()
        if self.inventory_page is not None:
            can_view_inventory = "inventory.view" in user.permissions
            self.sidebar.set_page_visible("inventory", can_view_inventory)
            if can_view_inventory:
                self.inventory_page.refresh()
        can_view_purchases = "purchases.view" in user.permissions
        if self.suppliers_page is not None:
            self.sidebar.set_page_visible("suppliers", can_view_purchases)
            if can_view_purchases:
                self.suppliers_page.refresh()
        if self.purchases_page is not None:
            self.sidebar.set_page_visible("purchases", can_view_purchases)
            if can_view_purchases:
                self.purchases_page.refresh()
        can_view_sales = "sales.view" in user.permissions
        if self.sales_page is not None:
            self.sidebar.set_page_visible("sales", can_view_sales)
            if can_view_sales:
                self.sales_page.refresh()
        if self.invoices_page is not None:
            self.sidebar.set_page_visible("invoices", can_view_sales)
            if can_view_sales:
                self.invoices_page.refresh()
        if self.payments_page is not None:
            can_view_payments = "payments.view" in user.permissions
            self.sidebar.set_page_visible("payments", can_view_payments)
            if can_view_payments:
                self.payments_page.refresh()
        if self.packing_page is not None:
            can_view_packing = "packing.view" in user.permissions
            self.sidebar.set_page_visible("packing", can_view_packing)
            if can_view_packing:
                self.packing_page.refresh()
        if self.dispatch_page is not None:
            can_view_dispatch = "dispatch.view" in user.permissions
            self.sidebar.set_page_visible("dispatch", can_view_dispatch)
            if can_view_dispatch:
                self.dispatch_page.refresh()
        if self.cloud_storage_page is not None:
            can_view_cloud = "cloud_storage.view" in user.permissions
            self.sidebar.set_page_visible("cloud_storage", can_view_cloud)
            if can_view_cloud:
                self.cloud_storage_page.refresh()
        can_view_communications = "communications.view" in user.permissions
        if self.whatsapp_page is not None:
            self.sidebar.set_page_visible("whatsapp", can_view_communications)
            if can_view_communications:
                self.whatsapp_page.refresh()
        if self.email_page is not None:
            self.sidebar.set_page_visible("email", can_view_communications)
            if can_view_communications:
                self.email_page.refresh()
        if self.operations_page is not None:
            can_view_operations = (
                "reports.view" in user.permissions or "audit.view" in user.permissions
            )
            self.sidebar.set_page_visible("operations", can_view_operations)
        self.navigate("dashboard")

    def logout(self) -> None:
        """End the service session and return to the login page."""

        if self._authentication_service is None:
            return
        self._authentication_service.logout()
        self.top_bar.set_authenticated_user(None)
        self._show_login()
