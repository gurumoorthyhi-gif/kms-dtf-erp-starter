"""Persistent Qt WebEngine profile construction and storage paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

from app.modules.whatsapp_workspace.constants import PROFILE_NAME


def chromium_user_agent(chromium_version: str) -> str:
    """Build a standards-based Chrome UA for WhatsApp's browser compatibility check."""

    version = chromium_version.strip()
    if not version or any(character not in "0123456789." for character in version):
        raise ValueError("A numeric Chromium version is required")
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{version} Safari/537.36"
    )


@dataclass(frozen=True, slots=True)
class WhatsAppProfilePaths:
    root: Path
    storage: Path
    cache: Path

    @classmethod
    def default(cls) -> WhatsAppProfilePaths:
        root = Path(user_data_path("KMS ERP", appauthor=False)) / "browser_profiles" / "whatsapp"
        return cls(root=root, storage=root / "storage", cache=root / "cache")

    def create(self) -> None:
        self.storage.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(parents=True, exist_ok=True)


def create_profile(parent, paths: WhatsAppProfilePaths | None = None):
    """Create a named disk-backed profile with persistent cookies."""

    from PySide6.QtWebEngineCore import QWebEngineProfile, qWebEngineChromiumVersion

    resolved = paths or WhatsAppProfilePaths.default()
    resolved.create()
    profile = QWebEngineProfile(PROFILE_NAME, parent)
    profile.setPersistentStoragePath(str(resolved.storage))
    profile.setCachePath(str(resolved.cache))
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )
    # WhatsApp rejects Qt WebEngine's default UA solely because it contains the
    # QtWebEngine product token. Advertise the actual bundled Chromium build.
    profile.setHttpUserAgent(chromium_user_agent(qWebEngineChromiumVersion()))
    profile.setHttpAcceptLanguage("en-US,en;q=0.9")
    return profile
