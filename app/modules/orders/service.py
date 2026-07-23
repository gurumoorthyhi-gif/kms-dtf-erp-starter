"""Order creation, totals, and workflow use cases."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.modules.authentication import AuthenticationService
from app.modules.orders.numbering import generate_order_number
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    OrderDetails,
    OrderInput,
    OrderItemDetails,
    OrderSummary,
    PricedOrderItem,
    StatusHistoryItem,
)
from app.modules.products import ProductService

ORDER_STATUSES = (
    "Draft",
    "Awaiting Artwork",
    "Designing",
    "Awaiting Approval",
    "Approved",
    "Gang Sheet Preparation",
    "Ready for Production",
    "Printing",
    "Powder and Cure",
    "Quality Check",
    "Cutting",
    "Packing",
    "Ready for Dispatch",
    "Dispatched",
    "Completed",
    "Cancelled",
)
PRIORITIES = ("Low", "Normal", "High", "Urgent")


class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        pricing_service: ProductService,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.pricing_service = pricing_service
        self.authentication_service = authentication_service

    def create_order(self, data: OrderInput) -> OrderDetails:
        self._require("orders.manage")
        if data.customer_id < 1 or not data.items:
            raise ValueError("A customer and at least one order item are required")
        if data.priority not in PRIORITIES:
            raise ValueError("Invalid order priority")
        priced_items = tuple(
            self._price_item(item.product_id, item.quantity) for item in data.items
        )
        subtotal = sum((item.subtotal for item in priced_items), Decimal("0"))
        discount = sum((item.discount for item in priced_items), Decimal("0"))
        tax = sum((item.tax for item in priced_items), Decimal("0"))
        total = sum((item.total for item in priced_items), Decimal("0"))
        if data.advance < 0 or data.advance > total:
            raise ValueError("Advance must be between zero and the order total")
        today = date.today()
        number = generate_order_number(today, self.repository.next_sequence(today))
        order = self.repository.create(
            order_number=number,
            customer_id=data.customer_id,
            items=priced_items,
            status="Draft",
            priority=data.priority,
            due_date=data.due_date,
            notes=data.notes.strip(),
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            advance=data.advance,
            balance=total - data.advance,
            changed_by_user_id=self._user_id(),
        )
        return self._details(order)

    def list_orders(self, query: str = "") -> list[OrderSummary]:
        self._require("orders.view")
        return [self._summary(order) for order in self.repository.list(query.strip())]

    def get_order(self, order_id: int) -> OrderDetails:
        self._require("orders.view")
        order = self.repository.get(order_id)
        if order is None:
            raise LookupError(f"Order not found: {order_id}")
        return self._details(order)

    def change_status(self, order_id: int, status: str, note: str = "") -> OrderDetails:
        self._require("orders.manage")
        if status not in ORDER_STATUSES:
            raise ValueError("Invalid order status")
        order = self.repository.change_status(
            order_id,
            status,
            note=note.strip(),
            changed_by_user_id=self._user_id(),
        )
        if order is None:
            raise LookupError(f"Order not found: {order_id}")
        return self._details(order)

    def _price_item(self, product_id: int, quantity: Decimal) -> PricedOrderItem:
        product = self.pricing_service.get_product(product_id)
        price = self.pricing_service.calculate_price(product_id, quantity)
        return PricedOrderItem(
            product_id=product.id,
            description=f"{product.code} - {product.name}",
            quantity=quantity,
            unit_price=price.unit_price,
            subtotal=price.subtotal,
            discount=price.discount,
            tax=price.tax,
            total=price.total,
        )

    def _require(self, permission: str) -> None:
        if self.authentication_service is not None:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if self.authentication_service is None:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user is not None else None

    @staticmethod
    def _summary(order) -> OrderSummary:
        return OrderSummary(
            order.id,
            order.order_number,
            order.customer.name,
            order.status,
            order.priority,
            order.due_date,
            order.total,
            order.balance,
        )

    @classmethod
    def _details(cls, order) -> OrderDetails:
        return OrderDetails(
            summary=cls._summary(order),
            notes=order.notes,
            subtotal=order.subtotal,
            discount=order.discount,
            tax=order.tax,
            advance=order.advance,
            items=tuple(
                OrderItemDetails(item.description, item.quantity, item.unit_price, item.total)
                for item in order.items
            ),
            status_history=tuple(
                StatusHistoryItem(
                    item.from_status,
                    item.to_status,
                    item.note,
                    item.changed_at,
                )
                for item in order.status_history
            ),
        )
