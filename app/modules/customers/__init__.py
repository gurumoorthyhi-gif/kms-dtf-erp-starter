"""Customer management module."""

from app.modules.customers.models import Customer, CustomerAddress, CustomerFileReference
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    AddressInput,
    CustomerDetails,
    CustomerInput,
    CustomerSummary,
)
from app.modules.customers.service import (
    CustomerNotFoundError,
    CustomerService,
    CustomerValidationError,
    DuplicateCustomerCodeError,
)

__all__ = [
    "AddressInput",
    "Customer",
    "CustomerAddress",
    "CustomerDetails",
    "CustomerFileReference",
    "CustomerInput",
    "CustomerNotFoundError",
    "CustomerRepository",
    "CustomerService",
    "CustomerSummary",
    "CustomerValidationError",
    "DuplicateCustomerCodeError",
]
