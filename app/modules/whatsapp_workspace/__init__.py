"""Embedded WhatsApp Web workspace with lazy Qt imports."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.whatsapp_workspace.host import WhatsAppWorkspaceHost

__all__ = ["WhatsAppWorkspaceHost"]


def __getattr__(name: str):
    if name == "WhatsAppWorkspaceHost":
        from app.modules.whatsapp_workspace.host import WhatsAppWorkspaceHost

        return WhatsAppWorkspaceHost
    raise AttributeError(name)
