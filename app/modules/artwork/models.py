"""Artwork library persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.modules.authentication.models import utc_now

if TYPE_CHECKING:
    from app.modules.customers.models import Customer
    from app.modules.orders.models import Order


class Artwork(Base):
    __tablename__ = "artworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    tags: Mapped[str] = mapped_column(String(500), default="", index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    customer: Mapped[Customer | None] = relationship()
    order: Mapped[Order | None] = relationship()
    versions: Mapped[list[ArtworkVersion]] = relationship(
        back_populates="artwork",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ArtworkVersion.version_number",
    )


class ArtworkVersion(Base):
    __tablename__ = "artwork_versions"
    __table_args__ = (UniqueConstraint("artwork_id", "version_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    original_path: Mapped[str] = mapped_column(String(500))
    preview_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    dpi_x: Mapped[int] = mapped_column(Integer, default=0)
    dpi_y: Mapped[int] = mapped_column(Integer, default=0)
    has_transparency: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    artwork: Mapped[Artwork] = relationship(back_populates="versions")
    approvals: Mapped[list[ArtworkApproval]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ArtworkApproval.created_at",
    )


class ArtworkApproval(Base):
    __tablename__ = "artwork_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_version_id: Mapped[int] = mapped_column(
        ForeignKey("artwork_versions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    version: Mapped[ArtworkVersion] = relationship(back_populates="approvals")
