"""Provider-neutral WhatsApp and email conversation persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.authentication.models import utc_now


class CommunicationMessage(Base):
    __tablename__ = "communication_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[str] = mapped_column(String(20), index=True)
    provider_message_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    thread_key: Mapped[str] = mapped_column(String(200), index=True)
    sender: Mapped[str] = mapped_column(String(254))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("communication_messages.id"), nullable=True
    )
    forwarded_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("communication_messages.id"), nullable=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    attachments: Mapped[list[CommunicationAttachment]] = relationship(
        back_populates="message", cascade="all, delete-orphan", lazy="selectin"
    )


class CommunicationAttachment(Base):
    __tablename__ = "communication_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("communication_messages.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(700))
    content_type: Mapped[str] = mapped_column(String(120), default="")
    message: Mapped[CommunicationMessage] = relationship(back_populates="attachments")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    template_type: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text)
