"""Packing and dispatch persistence with immutable histories."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.authentication.models import utc_now


class Packing(Base):
    __tablename__ = "packings"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    packing_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    packing_list: Mapped[str] = mapped_column(Text)
    package_count: Mapped[int] = mapped_column(default=1)
    package_weight: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    packed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order = relationship("Order")


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    packing_id: Mapped[int] = mapped_column(ForeignKey("packings.id"), index=True)
    dispatch_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    courier: Mapped[str] = mapped_column(String(80))
    tracking_number: Mapped[str] = mapped_column(String(100), index=True)
    dispatch_date: Mapped[date] = mapped_column(Date)
    delivery_status: Mapped[str] = mapped_column(String(30), index=True)
    shipping_label_path: Mapped[str] = mapped_column(String(500), default="")
    proof_of_dispatch_path: Mapped[str] = mapped_column(String(500), default="")
    override_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    order = relationship("Order")
    packing: Mapped[Packing] = relationship()
    events: Mapped[list[DispatchEvent]] = relationship(
        back_populates="dispatch",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DispatchEvent.created_at",
    )


class DispatchEvent(Base):
    __tablename__ = "dispatch_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(
        ForeignKey("dispatches.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30))
    details: Mapped[str] = mapped_column(Text, default="")
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    dispatch: Mapped[Dispatch] = relationship(back_populates="events")


class CustomerNotificationEvent(Base):
    __tablename__ = "customer_notification_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    recipient: Mapped[str] = mapped_column(String(254), default="")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
