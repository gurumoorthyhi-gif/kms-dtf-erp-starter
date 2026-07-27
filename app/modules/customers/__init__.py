"""Customer management module."""

from app.modules.customers.google_sheets import (
    CustomerSyncError,
    GoogleCustomerSheetSync,
)
from app.modules.customers.models import (
    Customer,
    CustomerAddress,
    CustomerFileReference,
    CustomerStorageDate,
)
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    AddressInput,
    CustomerDetails,
    CustomerInput,
    CustomerSummary,
)
from app.modules.customers.service import (
    CustomerDeletionError,
    CustomerNotFoundError,
    CustomerService,
    CustomerStorageDateExistsError,
    CustomerValidationError,
    DuplicateCustomerCodeError,
)

__all__ = [
    "AddressInput",
    "Customer",
    "CustomerAddress",
    "CustomerDetails",
    "CustomerDeletionError",
    "CustomerFileReference",
    "CustomerInput",
    "CustomerNotFoundError",
    "CustomerRepository",
    "CustomerService",
    "CustomerStorageDate",
    "CustomerStorageDateExistsError",
    "CustomerSummary",
    "CustomerSyncError",
    "CustomerValidationError",
    "DuplicateCustomerCodeError",
    "GoogleCustomerSheetSync",
]
