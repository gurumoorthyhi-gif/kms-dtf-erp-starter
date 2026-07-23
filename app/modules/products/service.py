"""Decimal-safe configurable pricing."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.modules.authentication import AuthenticationService
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductInput, ProductSummary

MONEY = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class PriceResult:
    unit_price: Decimal
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal


class ProductService:
    def __init__(
        self,
        repository: ProductRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create_category(self, name: str) -> tuple[int, str]:
        self._require("products.manage")
        normalized = name.strip()
        if not normalized:
            raise ValueError("Category name is required")
        category = self.repository.create_category(normalized)
        return category.id, category.name

    def list_categories(self) -> list[tuple[int, str]]:
        self._require("products.view")
        return [(item.id, item.name) for item in self.repository.list_categories()]

    def create_product(self, data: ProductInput) -> ProductSummary:
        self._require("products.manage")
        code = data.code.strip().upper()
        name = data.name.strip()
        if (
            not code
            or not name
            or data.base_price < 0
            or not Decimal("0") <= data.tax_rate <= Decimal("100")
        ):
            raise ValueError("Product code, name, price, or tax rate is invalid")
        product = self.repository.create_product(
            code=code,
            name=name,
            category_id=data.category_id,
            unit=data.unit.strip() or "piece",
            base_price=data.base_price,
            tax_rate=data.tax_rate,
            size=data.size.strip(),
            colour=data.colour.strip(),
            gsm=data.gsm.strip(),
            style=data.style.strip(),
        )
        return self._summary(product)

    def list_products(self, query: str = "") -> list[ProductSummary]:
        self._require("products.view")
        return [self._summary(item) for item in self.repository.list_products(query)]

    def get_product(self, product_id: int) -> ProductSummary:
        self._require("products.view")
        product = self.repository.get(product_id)
        if product is None:
            raise LookupError("Product not found")
        return self._summary(product)

    def add_price_rule(self, product_id: int, minimum: Decimal, unit_price: Decimal) -> None:
        self._require("products.manage")
        if minimum <= 0 or unit_price < 0:
            raise ValueError("Price rule values are invalid")
        self.repository.add_price_rule(product_id, minimum, unit_price)

    def add_discount_rule(self, name: str, minimum_subtotal: Decimal, percentage: Decimal) -> None:
        self._require("products.manage")
        if (
            not name.strip()
            or minimum_subtotal < 0
            or not Decimal("0") <= percentage <= Decimal("100")
        ):
            raise ValueError("Discount rule values are invalid")
        self.repository.add_discount(name.strip(), minimum_subtotal, percentage)

    def add_tax_configuration(self, name: str, percentage: Decimal) -> None:
        self._require("products.manage")
        if not name.strip() or not Decimal("0") <= percentage <= Decimal("100"):
            raise ValueError("Tax percentage is invalid")
        self.repository.add_tax(name.strip(), percentage)

    def calculate_price(self, product_id: int, quantity: Decimal) -> PriceResult:
        self._require("products.view")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        product = self.repository.get(product_id)
        if product is None or not product.is_active:
            raise LookupError("Product not found")
        applicable = [rule for rule in product.price_rules if quantity >= rule.minimum_quantity]
        unit_price = (
            max(applicable, key=lambda x: x.minimum_quantity).unit_price
            if applicable
            else product.base_price
        )
        subtotal = (unit_price * quantity).quantize(MONEY, rounding=ROUND_HALF_UP)
        rule = next(
            (
                item
                for item in self.repository.list_discounts()
                if subtotal >= item.minimum_subtotal
            ),
            None,
        )
        discount = (subtotal * rule.percentage / Decimal("100") if rule else Decimal("0")).quantize(
            MONEY, rounding=ROUND_HALF_UP
        )
        taxable = subtotal - discount
        tax = (taxable * product.tax_rate / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
        return PriceResult(unit_price, subtotal, discount, tax, taxable + tax)

    def _require(self, permission: str) -> None:
        if self.authentication_service is not None:
            self.authentication_service.require_permission(permission)

    @staticmethod
    def _summary(product) -> ProductSummary:
        return ProductSummary(
            product.id,
            product.code,
            product.name,
            product.category.name,
            product.unit,
            product.base_price,
            product.tax_rate,
            product.is_active,
        )
