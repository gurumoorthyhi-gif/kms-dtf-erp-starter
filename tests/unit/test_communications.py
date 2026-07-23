from pathlib import Path
from uuid import uuid4

from app.database import Base, create_database_engine, create_session_factory
from app.modules.communications import CommunicationService, ProviderMessage
from app.modules.customers import models as customer_models
from app.modules.orders import models as order_models

_ = (customer_models, order_models)


class MockProvider:
    def __init__(self) -> None:
        self.inbox = []
        self.sent = []

    def send(self, recipient, body, *, subject="", attachments=(), reply_to=""):
        message = ProviderMessage(
            f"sent-{uuid4().hex}", "thread-1", "erp", recipient, body, subject
        )
        self.sent.append((message, attachments, reply_to))
        return message

    def receive(self):
        messages, self.inbox = self.inbox, []
        return messages

    def download_media(self, media_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"media:{media_id}".encode())
        return destination


def make_service(tmp_path: Path, channel="whatsapp"):
    engine = create_database_engine(f"sqlite:///{tmp_path / f'{channel}.db'}")
    Base.metadata.create_all(engine)
    provider = MockProvider()
    service = CommunicationService(
        create_session_factory(engine), channel, provider, tmp_path / "media"
    )
    return engine, provider, service


def test_mock_whatsapp_send_receive_media_and_history(tmp_path: Path) -> None:
    engine, provider, service = make_service(tmp_path)
    sent = service.send("919876543210", "Invoice attached")
    provider.inbox.append(
        ProviderMessage(
            "incoming-1",
            "thread-1",
            "919876543210",
            "erp",
            "Thank you",
            attachments=(("receipt.jpg", "media-1"),),
        )
    )

    assert service.receive() == 1
    assert service.receive() == 0
    history = service.history()
    assert {item.direction for item in history} == {"inbound", "outbound"}
    assert history[0].attachments[0].filename == "receipt.jpg"
    assert sent.provider_message_id.startswith("sent-")
    engine.dispose()


def test_mock_email_reply_forward_attachment_and_links(tmp_path: Path) -> None:
    engine, provider, service = make_service(tmp_path, "email")
    original = service.send("customer@example.com", "Quotation", subject="Quote")
    reply = service.send(
        "customer@example.com",
        "Reply",
        subject="Re: Quote",
        reply_to_id=original.id,
    )
    forwarded = service.send(
        "owner@example.com",
        "Forwarded quotation",
        forwarded_from_id=original.id,
    )

    assert provider.sent[1][2] == original.provider_message_id
    assert reply.reply_to_id == original.id
    assert forwarded.forwarded_from_id == original.id
    engine.dispose()


def test_templates_cover_business_message_types(tmp_path: Path) -> None:
    engine, provider, service = make_service(tmp_path, "email")
    for template_type in ("quotation", "invoice", "artwork_approval", "dispatch"):
        service.save_template(
            template_type,
            template_type,
            f"{template_type}: {{number}}",
            "KMS {number}",
        )
        sent = service.send_template(template_type, "customer@example.com", {"number": "101"})
        assert sent.body.endswith("101")
    assert len(provider.sent) == 4
    engine.dispose()


def test_duplicate_inbound_provider_message_is_not_stored_twice(tmp_path: Path) -> None:
    engine, provider, service = make_service(tmp_path)
    incoming = ProviderMessage("same-id", "thread", "customer", "erp", "Hello")
    provider.inbox.extend((incoming, incoming))

    assert service.receive() == 1
    assert len(service.history()) == 1
    engine.dispose()
