"""Application pages."""

from app.ui.pages.ai_tools import AIToolsPage
from app.ui.pages.artwork import ArtworkDetailsDialog, ArtworkLibraryPage, ArtworkUploadDialog
from app.ui.pages.artwork_studio import ArtworkStudioPage, BeforeAfterView, ImageCanvas
from app.ui.pages.cloud_storage import CloudStoragePage
from app.ui.pages.communications import EmailInboxPage, WhatsAppInboxPage
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.gang_sheets import GangSheetCanvas, GangSheetPage, LayoutHistory
from app.ui.pages.inventory import (
    InventoryItemDialog,
    InventoryPage,
    PurchasesPage,
    SuppliersPage,
)
from app.ui.pages.login import LoginPage
from app.ui.pages.operations import OperationsPage
from app.ui.pages.orders import OrderCreationDialog, OrderDetailsDialog, OrdersPage
from app.ui.pages.production import ProductionHistoryDialog, ProductionPage
from app.ui.pages.products import ProductFormDialog, ProductsPage
from app.ui.pages.sales import InvoicesPage, PaymentsPage, SalesPage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.shipping import DispatchPage, PackingPage

__all__ = [
    "CustomerDetailsDialog",
    "CustomerFormDialog",
    "CustomersPage",
    "DashboardPage",
    "CloudStoragePage",
    "EmailInboxPage",
    "WhatsAppInboxPage",
    "GangSheetCanvas",
    "GangSheetPage",
    "LayoutHistory",
    "ArtworkDetailsDialog",
    "AIToolsPage",
    "ArtworkLibraryPage",
    "ArtworkUploadDialog",
    "ArtworkStudioPage",
    "BeforeAfterView",
    "ImageCanvas",
    "InventoryItemDialog",
    "InventoryPage",
    "LoginPage",
    "OrderCreationDialog",
    "OrderDetailsDialog",
    "OrdersPage",
    "OperationsPage",
    "ProductFormDialog",
    "ProductsPage",
    "ProductionHistoryDialog",
    "ProductionPage",
    "PurchasesPage",
    "SettingsPage",
    "InvoicesPage",
    "PaymentsPage",
    "SalesPage",
    "DispatchPage",
    "PackingPage",
    "SuppliersPage",
]
from app.ui.pages.customers import CustomerDetailsDialog, CustomerFormDialog, CustomersPage
