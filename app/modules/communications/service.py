"""Shared communication workflows and conversation history."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.authentication import AuthenticationService
from app.modules.communications.models import (
    CommunicationAttachment,
    CommunicationMessage,
    MessageTemplate,
)
from app.modules.communications.providers import CommunicationProvider

TEMPLATE_TYPES = ("artwork_approval", "quotation", "invoice", "dispatch")


class CommunicationService:
    def __init__(
        self,
        factory: SessionFactory,
        channel: str,
        provider: CommunicationProvider,
        media_root: Path,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.factory, self.channel, self.provider = factory, channel, provider
        self.media_root = media_root.resolve()
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.authentication_service = authentication_service

    def send(
        self,
        recipient: str,
        body: str,
        *,
        subject: str = "",
        customer_id: int | None = None,
        order_id: int | None = None,
        attachments: tuple[Path, ...] = (),
        reply_to_id: int | None = None,
        forwarded_from_id: int | None = None,
    ) -> CommunicationMessage:
        self._require("communications.send")
        if not recipient.strip() or not body.strip():
            raise ValueError("Recipient and message are required")
        reply_provider_id = ""
        if reply_to_id:
            reply_provider_id = self.get(reply_to_id).provider_message_id
        sent = self.provider.send(
            recipient.strip(),
            body.strip(),
            subject=subject.strip(),
            attachments=attachments,
            reply_to=reply_provider_id,
        )
        return self._store(sent, "outbound", customer_id, order_id, reply_to_id, forwarded_from_id)

    def receive(self) -> int:
        self._require("communications.receive")
        count = 0
        for message in self.provider.receive():
            with session_scope(self.factory) as session:
                exists = session.scalar(
                    select(CommunicationMessage.id).where(
                        CommunicationMessage.provider_message_id == message.provider_id
                    )
                )
            if not exists:
                self._store(message, "inbound", None, None, None, None)
                count += 1
        return count

    def attach(
        self, message_id: int, *, customer_id: int | None, order_id: int | None
    ) -> CommunicationMessage:
        self._require("communications.manage")
        with session_scope(self.factory) as session:
            message = session.get(CommunicationMessage, message_id)
            if not message:
                raise LookupError("Message not found")
            message.customer_id, message.order_id = customer_id, order_id
        return self.get(message_id)

    def save_template(self, template_type: str, name: str, body: str, subject: str = "") -> None:
        self._require("communications.manage")
        if template_type not in TEMPLATE_TYPES or not name.strip() or not body.strip():
            raise ValueError("Invalid message template")
        with session_scope(self.factory) as session:
            session.add(
                MessageTemplate(
                    channel=self.channel,
                    template_type=template_type,
                    name=name.strip(),
                    subject=subject.strip(),
                    body=body.strip(),
                )
            )

    def send_template(
        self,
        template_type: str,
        recipient: str,
        values: dict[str, str],
        **links,
    ) -> CommunicationMessage:
        with session_scope(self.factory) as session:
            template = session.scalar(
                select(MessageTemplate).where(
                    MessageTemplate.channel == self.channel,
                    MessageTemplate.template_type == template_type,
                )
            )
            if not template:
                raise LookupError("Message template not found")
            body, subject = template.body.format_map(values), template.subject.format_map(values)
        return self.send(recipient, body, subject=subject, **links)

    def history(
        self, *, customer_id: int | None = None, order_id: int | None = None
    ) -> list[CommunicationMessage]:
        self._require("communications.view")
        with session_scope(self.factory) as session:
            statement = (
                select(CommunicationMessage)
                .where(CommunicationMessage.channel == self.channel)
                .options(selectinload(CommunicationMessage.attachments))
            )
            if customer_id:
                statement = statement.where(CommunicationMessage.customer_id == customer_id)
            if order_id:
                statement = statement.where(CommunicationMessage.order_id == order_id)
            return list(session.scalars(statement.order_by(CommunicationMessage.sent_at.desc())))

    def get(self, message_id: int) -> CommunicationMessage:
        with session_scope(self.factory) as session:
            message = session.scalar(
                select(CommunicationMessage)
                .where(CommunicationMessage.id == message_id)
                .options(selectinload(CommunicationMessage.attachments))
            )
            if not message:
                raise LookupError("Message not found")
            return message

    def _store(self, data, direction, customer_id, order_id, reply_id, forward_id):
        with session_scope(self.factory) as session:
            message = CommunicationMessage(
                channel=self.channel,
                direction=direction,
                provider_message_id=data.provider_id,
                thread_key=data.thread_key,
                sender=data.sender,
                recipient=data.recipient,
                subject=data.subject,
                body=data.body,
                customer_id=customer_id,
                order_id=order_id,
                reply_to_id=reply_id,
                forwarded_from_id=forward_id,
                created_by_user_id=self._user_id(),
            )
            for filename, media_id in data.attachments:
                target = self.media_root / f"{uuid4().hex}-{Path(filename).name}"
                self.provider.download_media(media_id, target)
                message.attachments.append(
                    CommunicationAttachment(
                        filename=Path(filename).name,
                        object_key=target.relative_to(self.media_root).as_posix(),
                    )
                )
            session.add(message)
            session.flush()
            message_id = message.id
        return self.get(message_id)

    def _require(self, permission: str) -> None:
        if self.authentication_service:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if not self.authentication_service:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None
