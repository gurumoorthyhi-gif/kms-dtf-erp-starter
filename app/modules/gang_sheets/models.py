"""Gang sheet layout persistence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.authentication.models import utc_now

if TYPE_CHECKING:
    from app.modules.artwork.models import ArtworkVersion
    from app.modules.orders.models import Order


class GangSheet(Base):
    __tablename__ = "gang_sheets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    width_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    length_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    margin_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    spacing_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    order: Mapped[Order | None] = relationship()
    items: Mapped[list[GangSheetItem]] = relationship(
        back_populates="gang_sheet",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="GangSheetItem.z_index",
    )


class GangSheetItem(Base):
    __tablename__ = "gang_sheet_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    gang_sheet_id: Mapped[int] = mapped_column(
        ForeignKey("gang_sheets.id", ondelete="CASCADE"), index=True
    )
    artwork_version_id: Mapped[int] = mapped_column(ForeignKey("artwork_versions.id"))
    x_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    y_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    width_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    height_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    rotation_degrees: Mapped[int] = mapped_column(default=0)
    z_index: Mapped[int] = mapped_column(default=0)
    gang_sheet: Mapped[GangSheet] = relationship(back_populates="items")
    artwork_version: Mapped[ArtworkVersion] = relationship()
