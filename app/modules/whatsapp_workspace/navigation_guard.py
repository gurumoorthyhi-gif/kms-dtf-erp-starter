"""Top-level navigation policy for the embedded WhatsApp browser."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

ALLOWED_HOSTS = (
    "whatsapp.com",
    "whatsapp.net",
    "facebook.com",
    "fbcdn.net",
)


def host_is_allowed(host: str | None) -> bool:
    """Return whether a host belongs to WhatsApp's required web properties."""

    normalized = (host or "").strip(".").lower()
    return any(normalized == root or normalized.endswith(f".{root}") for root in ALLOWED_HOSTS)


def top_level_url_is_allowed(url: str) -> bool:
    """Permit HTTPS navigation only to the central allow-list."""

    parsed = urlsplit(url)
    return parsed.scheme.lower() == "https" and host_is_allowed(parsed.hostname)


def redact_url(url: str) -> str:
    """Remove query strings, fragments, credentials, and ports before logging."""

    parsed = urlsplit(url)
    host = parsed.hostname or ""
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))

