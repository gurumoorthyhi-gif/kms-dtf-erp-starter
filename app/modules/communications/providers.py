"""Interfaces for API-based WhatsApp and email providers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    provider_id: str
    thread_key: str
    sender: str
    recipient: str
    body: str
    subject: str = ""
    attachments: tuple[tuple[str, str], ...] = ()


class CommunicationProvider(Protocol):
    def send(
        self,
        recipient: str,
        body: str,
        *,
        subject: str = "",
        attachments: tuple[Path, ...] = (),
        reply_to: str = "",
    ) -> ProviderMessage: ...

    def receive(self) -> list[ProviderMessage]: ...

    def download_media(self, media_id: str, destination: Path) -> Path: ...


class WhatsAppProvider(CommunicationProvider, Protocol):
    """Official/API provider contract; no browser-session dependency."""


class EmailProvider(CommunicationProvider, Protocol):
    """SMTP/API and inbox provider contract."""


class UnconfiguredProvider:
    def send(self, *args, **kwargs):
        raise RuntimeError("Communication provider is not configured")

    def receive(self) -> list[ProviderMessage]:
        return []

    def download_media(self, media_id: str, destination: Path) -> Path:
        raise RuntimeError("Communication provider is not configured")
