"""Customer persistence models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.modules.authentication.models import utc_now


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    business_name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20))
    whatsapp_number: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    gst_number: Mapped[str] = mapped_column(String(15), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    addresses: Mapped[list[CustomerAddress]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    file_references: Mapped[list[CustomerFileReference]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"
    __table_args__ = (UniqueConstraint("customer_id", "address_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    address_type: Mapped[str] = mapped_column(String(20))
    line1: Mapped[str] = mapped_column(String(200), default="")
    line2: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(100), default="")
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    country: Mapped[str] = mapped_column(String(80), default="India")

    customer: Mapped[Customer] = relationship(back_populates="addresses")


class CustomerFileReference(Base):
    __tablename__ = "customer_file_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    stored_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    customer: Mapped[Customer] = relationship(back_populates="file_references")
