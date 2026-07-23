"""Production jobs, immutable events, and quality checks."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.authentication.models import utc_now

if TYPE_CHECKING:
    from app.modules.authentication.models import User
    from app.modules.gang_sheets.models import GangSheet
    from app.modules.orders.models import Order


class ProductionJob(Base):
    __tablename__ = "production_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    gang_sheet_id: Mapped[int | None] = mapped_column(ForeignKey("gang_sheets.id"), nullable=True)
    stage: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(20), default="Normal", index=True)
    machine_name: Mapped[str] = mapped_column(String(100), default="")
    operator_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    pause_reason: Mapped[str] = mapped_column(Text, default="")
    reprint_count: Mapped[int] = mapped_column(default=0)
    wastage_metres: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    order: Mapped[Order] = relationship()
    gang_sheet: Mapped[GangSheet | None] = relationship()
    operator: Mapped[User | None] = relationship(foreign_keys=[operator_user_id])
    events: Mapped[list[ProductionEvent]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductionEvent.created_at",
    )
    quality_checks: Mapped[list[QualityCheck]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="QualityCheck.checked_at",
    )


class ProductionEvent(Base):
    __tablename__ = "production_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    production_job_id: Mapped[int] = mapped_column(
        ForeignKey("production_jobs.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(40))
    from_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    job: Mapped[ProductionJob] = relationship(back_populates="events")


class QualityCheck(Base):
    __tablename__ = "quality_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    production_job_id: Mapped[int] = mapped_column(
        ForeignKey("production_jobs.id", ondelete="CASCADE"), index=True
    )
    passed: Mapped[bool] = mapped_column(Boolean)
    print_quality_ok: Mapped[bool] = mapped_column(Boolean)
    colour_ok: Mapped[bool] = mapped_column(Boolean)
    curing_ok: Mapped[bool] = mapped_column(Boolean)
    notes: Mapped[str] = mapped_column(Text, default="")
    inspector_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    job: Mapped[ProductionJob] = relationship(back_populates="quality_checks")
