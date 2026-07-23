"""Inventory and purchase repositories with transactional stock posting."""

from __future__ import annotations

import builtins
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.inventory.models import (
    InventoryItem,
    InventoryMovement,
    Purchase,
    PurchaseItem,
    Supplier,
)
from app.modules.inventory.schemas import InventoryItemInput, PurchaseInput, SupplierInput


class InventoryRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def create(self, data: InventoryItemInput) -> InventoryItem:
        with session_scope(self.factory) as session:
            item = InventoryItem(
                sku=data.sku,
                name=data.name,
                item_type=data.item_type,
                unit=data.unit,
                reorder_level=data.reorder_level,
                unit_cost=data.unit_cost,
                allow_negative=data.allow_negative,
            )
            session.add(item)
            session.flush()
            item_id = item.id
        return self.get(item_id)

    def list(self) -> list[InventoryItem]:
        with session_scope(self.factory) as session:
            return list(session.scalars(select(InventoryItem).order_by(InventoryItem.name)))

    def get(self, item_id: int) -> InventoryItem:
        with session_scope(self.factory) as session:
            item = session.get(InventoryItem, item_id)
            if item is None:
                raise LookupError("Inventory item not found")
            return item

    def move(
        self,
        item_id: int,
        change: Decimal,
        *,
        movement_type: str,
        reference: str,
        notes: str,
        actor_user_id: int | None,
    ) -> InventoryItem:
        with session_scope(self.factory) as session:
            item = session.get(InventoryItem, item_id)
            if item is None:
                raise LookupError("Inventory item not found")
            balance = item.quantity_on_hand + change
            if balance < 0 and not item.allow_negative:
                raise ValueError("Movement would create negative stock")
            item.quantity_on_hand = balance
            session.add(
                InventoryMovement(
                    inventory_item_id=item_id,
                    movement_type=movement_type,
                    quantity_change=change,
                    balance_after=balance,
                    reference=reference,
                    notes=notes,
                    actor_user_id=actor_user_id,
                )
            )
        return self.get(item_id)

    def movements(self, item_id: int) -> builtins.list[InventoryMovement]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    select(InventoryMovement)
                    .where(InventoryMovement.inventory_item_id == item_id)
                    .order_by(InventoryMovement.created_at)
                )
            )


class PurchaseRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def create_supplier(self, data: SupplierInput) -> Supplier:
        with session_scope(self.factory) as session:
            supplier = Supplier(
                code=data.code,
                name=data.name,
                contact_name=data.contact_name,
                phone=data.phone,
                email=data.email,
                gst_number=data.gst_number,
                address=data.address,
                notes=data.notes,
            )
            session.add(supplier)
            session.flush()
            supplier_id = supplier.id
        return self.get_supplier(supplier_id)

    def list_suppliers(self) -> list[Supplier]:
        with session_scope(self.factory) as session:
            return list(session.scalars(select(Supplier).order_by(Supplier.name)))

    def get_supplier(self, supplier_id: int) -> Supplier:
        with session_scope(self.factory) as session:
            supplier = session.get(Supplier, supplier_id)
            if supplier is None:
                raise LookupError("Supplier not found")
            return supplier

    def create_purchase(self, number: str, data: PurchaseInput) -> Purchase:
        with session_scope(self.factory) as session:
            if session.get(Supplier, data.supplier_id) is None:
                raise LookupError("Supplier not found")
            total = Decimal("0")
            purchase = Purchase(
                purchase_number=number,
                supplier_id=data.supplier_id,
                status="Ordered",
                order_date=date.today(),
                expected_date=data.expected_date,
                total=Decimal("0"),
                notes=data.notes,
            )
            for entry in data.items:
                if session.get(InventoryItem, entry.inventory_item_id) is None:
                    raise LookupError("Inventory item not found")
                line_total = entry.quantity * entry.unit_cost
                total += line_total
                purchase.items.append(
                    PurchaseItem(
                        inventory_item_id=entry.inventory_item_id,
                        quantity=entry.quantity,
                        unit_cost=entry.unit_cost,
                        line_total=line_total,
                    )
                )
            purchase.total = total
            session.add(purchase)
            session.flush()
            purchase_id = purchase.id
        return self.get_purchase(purchase_id)

    def next_purchase_sequence(self, prefix: str) -> int:
        with session_scope(self.factory) as session:
            numbers = session.scalars(
                select(Purchase.purchase_number).where(Purchase.purchase_number.like(f"{prefix}%"))
            )
            values = [
                int(number.removeprefix(prefix))
                for number in numbers
                if number.removeprefix(prefix).isdigit()
            ]
            return max(values, default=0) + 1

    def list_purchases(self) -> list[Purchase]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(self._purchase_statement().order_by(Purchase.order_date.desc()))
            )

    def get_purchase(self, purchase_id: int) -> Purchase:
        with session_scope(self.factory) as session:
            purchase = session.scalar(self._purchase_statement().where(Purchase.id == purchase_id))
            if purchase is None:
                raise LookupError("Purchase not found")
            return purchase

    def receive(self, purchase_id: int, actor_user_id: int | None) -> Purchase:
        """Post the receipt and every stock movement in one database transaction."""

        with session_scope(self.factory) as session:
            purchase = session.scalar(
                select(Purchase)
                .where(Purchase.id == purchase_id)
                .options(selectinload(Purchase.items))
            )
            if purchase is None:
                raise LookupError("Purchase not found")
            if purchase.status == "Received":
                raise ValueError("Purchase is already received")
            for entry in purchase.items:
                item = session.get(InventoryItem, entry.inventory_item_id)
                if item is None:
                    raise LookupError("Inventory item not found")
                balance = item.quantity_on_hand + entry.quantity
                item.quantity_on_hand = balance
                item.unit_cost = entry.unit_cost
                entry.received_quantity = entry.quantity
                session.add(
                    InventoryMovement(
                        inventory_item_id=item.id,
                        movement_type="purchase_receipt",
                        quantity_change=entry.quantity,
                        balance_after=balance,
                        reference=purchase.purchase_number,
                        notes="Purchase receipt posted",
                        actor_user_id=actor_user_id,
                    )
                )
            purchase.status = "Received"
            purchase.received_date = date.today()
        return self.get_purchase(purchase_id)

    @staticmethod
    def _purchase_statement():
        return select(Purchase).options(
            selectinload(Purchase.supplier),
            selectinload(Purchase.items).selectinload(PurchaseItem.inventory_item),
        )
