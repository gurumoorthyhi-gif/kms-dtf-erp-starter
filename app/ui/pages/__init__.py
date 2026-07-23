"""Application pages."""

from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.login import LoginPage
from app.ui.pages.products import ProductFormDialog, ProductsPage
from app.ui.pages.settings import SettingsPage

__all__ = [
    "CustomerDetailsDialog",
    "CustomerFormDialog",
    "CustomersPage",
    "DashboardPage",
    "LoginPage",
    "ProductFormDialog",
    "ProductsPage",
    "SettingsPage",
]
from app.ui.pages.customers import CustomerDetailsDialog, CustomerFormDialog, CustomersPage
