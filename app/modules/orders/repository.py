"""Order persistence and status history."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.orders.numbering import order_number_prefix
from app.modules.orders.schemas import PricedOrderItem


class OrderRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def next_sequence(self, day: date) -> int:
        prefix = order_number_prefix(day)
        with session_scope(self.factory) as session:
            numbers = session.scalars(
                select(Order.order_number).where(Order.order_number.like(f"{prefix}%"))
            )
            sequences = [
                int(number.removeprefix(prefix))
                for number in numbers
                if number.removeprefix(prefix).isdigit()
            ]
            return max(sequences, default=0) + 1

    def create(
        self,
        *,
        order_number: str,
        customer_id: int,
        items: tuple[PricedOrderItem, ...],
        status: str,
        priority: str,
        due_date: date | None,
        notes: str,
        subtotal: Decimal,
        discount: Decimal,
        tax: Decimal,
        total: Decimal,
        advance: Decimal,
        balance: Decimal,
        changed_by_user_id: int | None,
    ) -> Order:
        with session_scope(self.factory) as session:
            order = Order(
                order_number=order_number,
                customer_id=customer_id,
                status=status,
                priority=priority,
                due_date=due_date,
                notes=notes,
                subtotal=subtotal,
                discount=discount,
                tax=tax,
                total=total,
                advance=advance,
                balance=balance,
            )
            order.items.extend(
                OrderItem(
                    product_id=item.product_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    discount=item.discount,
                    tax=item.tax,
                    total=item.total,
                )
                for item in items
            )
            order.status_history.append(
                OrderStatusHistory(
                    from_status=None,
                    to_status=status,
                    note="Order created",
                    changed_by_user_id=changed_by_user_id,
                )
            )
            session.add(order)
            session.flush()
            order_id = order.id
        created = self.get(order_id)
        if created is None:
            raise RuntimeError("Order could not be reloaded")
        return created

    def list(self, query: str = "") -> list[Order]:
        from app.modules.customers.models import Customer

        with session_scope(self.factory) as session:
            statement = select(Order).join(Order.customer).options(selectinload(Order.customer))
            if query:
                statement = statement.where(
                    Order.order_number.ilike(f"%{query}%") | Customer.name.ilike(f"%{query}%")
                )
            return list(session.scalars(statement.order_by(Order.created_at.desc())))

    def get(self, order_id: int) -> Order | None:
        with session_scope(self.factory) as session:
            return session.scalar(
                select(Order)
                .where(Order.id == order_id)
                .options(
                    selectinload(Order.customer),
                    selectinload(Order.items),
                    selectinload(Order.status_history),
                )
            )

    def change_status(
        self,
        order_id: int,
        status: str,
        *,
        note: str,
        changed_by_user_id: int | None,
    ) -> Order | None:
        with session_scope(self.factory) as session:
            order = session.get(Order, order_id)
            if order is None:
                return None
            previous = order.status
            order.status = status
            session.add(
                OrderStatusHistory(
                    order_id=order.id,
                    from_status=previous,
                    to_status=status,
                    note=note,
                    changed_by_user_id=changed_by_user_id,
                )
            )
        return self.get(order_id)
