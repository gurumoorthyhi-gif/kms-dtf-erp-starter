"""Transactional packing and dispatch persistence."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.authentication.models import utc_now
from app.modules.orders.models import Order
from app.modules.shipping.models import (
    CustomerNotificationEvent,
    Dispatch,
    DispatchEvent,
    Packing,
)


class ShippingRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def next_sequence(self, prefix: str, column) -> int:
        with session_scope(self.factory) as session:
            values = session.scalars(select(column).where(column.like(f"{prefix}%")))
            numbers = [
                int(value.removeprefix(prefix))
                for value in values
                if value.removeprefix(prefix).isdigit()
            ]
            return max(numbers, default=0) + 1

    def create_packing(
        self,
        order_id: int,
        number: str,
        count: int,
        weight: Decimal,
        notes: str,
        user_id: int | None,
    ) -> Packing:
        with session_scope(self.factory) as session:
            order = session.scalar(
                select(Order).where(Order.id == order_id).options(selectinload(Order.items))
            )
            if order is None:
                raise LookupError("Order not found")
            lines = "\n".join(f"{item.description} — {item.quantity}" for item in order.items)
            packing = Packing(
                order_id=order.id,
                packing_number=number,
                packing_list=lines,
                package_count=count,
                package_weight=weight,
                notes=notes,
                packed_by_user_id=user_id,
            )
            session.add(packing)
            session.flush()
            packing_id = packing.id
        return self.get_packing(packing_id)

    def complete_packing(self, packing_id: int) -> Packing:
        with session_scope(self.factory) as session:
            packing = session.get(Packing, packing_id)
            if packing is None:
                raise LookupError("Packing record not found")
            packing.is_complete = True
            packing.completed_at = utc_now()
        return self.get_packing(packing_id)

    def get_packing(self, packing_id: int) -> Packing:
        with session_scope(self.factory) as session:
            packing = session.scalar(
                select(Packing)
                .where(Packing.id == packing_id)
                .options(selectinload(Packing.order).selectinload(Order.customer))
            )
            if packing is None:
                raise LookupError("Packing record not found")
            return packing

    def list_packings(self) -> list[Packing]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    select(Packing)
                    .options(selectinload(Packing.order).selectinload(Order.customer))
                    .order_by(Packing.created_at.desc())
                )
            )

    def create_dispatch(
        self,
        packing_id: int,
        number: str,
        courier: str,
        tracking: str,
        proof_path: str,
        override: bool,
        user_id: int | None,
    ) -> Dispatch:
        with session_scope(self.factory) as session:
            packing = session.get(Packing, packing_id)
            if packing is None:
                raise LookupError("Packing record not found")
            if not packing.is_complete and not override:
                raise ValueError("Packing must be complete before dispatch")
            dispatch = Dispatch(
                order_id=packing.order_id,
                packing_id=packing.id,
                dispatch_number=number,
                courier=courier,
                tracking_number=tracking,
                dispatch_date=date.today(),
                delivery_status="Dispatched",
                proof_of_dispatch_path=proof_path,
                override_authorized=override,
                created_by_user_id=user_id,
            )
            dispatch.events.append(
                DispatchEvent(
                    from_status=None,
                    to_status="Dispatched",
                    details="Dispatch created"
                    + (" with authorized packing override" if override else ""),
                    actor_user_id=user_id,
                )
            )
            session.add(dispatch)
            session.flush()
            session.add(
                CustomerNotificationEvent(
                    order_id=packing.order_id,
                    dispatch_id=dispatch.id,
                    event_type="dispatch_created",
                    message=f"Order dispatched via {courier}; tracking {tracking}",
                )
            )
            dispatch_id = dispatch.id
        return self.get_dispatch(dispatch_id)

    def update_delivery(
        self, dispatch_id: int, status: str, details: str, user_id: int | None
    ) -> Dispatch:
        with session_scope(self.factory) as session:
            dispatch = session.get(Dispatch, dispatch_id)
            if dispatch is None:
                raise LookupError("Dispatch not found")
            previous = dispatch.delivery_status
            dispatch.delivery_status = status
            session.add(
                DispatchEvent(
                    dispatch_id=dispatch.id,
                    from_status=previous,
                    to_status=status,
                    details=details,
                    actor_user_id=user_id,
                )
            )
            session.add(
                CustomerNotificationEvent(
                    order_id=dispatch.order_id,
                    dispatch_id=dispatch.id,
                    event_type="delivery_status",
                    message=f"Delivery status updated to {status}",
                )
            )
        return self.get_dispatch(dispatch_id)

    def set_label_path(self, dispatch_id: int, path: str) -> Dispatch:
        with session_scope(self.factory) as session:
            dispatch = session.get(Dispatch, dispatch_id)
            if dispatch is None:
                raise LookupError("Dispatch not found")
            dispatch.shipping_label_path = path
        return self.get_dispatch(dispatch_id)

    def get_dispatch(self, dispatch_id: int) -> Dispatch:
        with session_scope(self.factory) as session:
            dispatch = session.scalar(
                select(Dispatch)
                .where(Dispatch.id == dispatch_id)
                .options(
                    selectinload(Dispatch.order).selectinload(Order.customer),
                    selectinload(Dispatch.events),
                    selectinload(Dispatch.packing),
                )
            )
            if dispatch is None:
                raise LookupError("Dispatch not found")
            return dispatch

    def list_dispatches(self) -> list[Dispatch]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    select(Dispatch)
                    .options(
                        selectinload(Dispatch.order).selectinload(Order.customer),
                        selectinload(Dispatch.events),
                    )
                    .order_by(Dispatch.created_at.desc())
                )
            )

    def notification_count(self, dispatch_id: int) -> int:
        with session_scope(self.factory) as session:
            return len(
                list(
                    session.scalars(
                        select(CustomerNotificationEvent).where(
                            CustomerNotificationEvent.dispatch_id == dispatch_id
                        )
                    )
                )
            )
