"""Persistent Qt WebEngine profile construction and storage paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

from app.modules.whatsapp_workspace.constants import PROFILE_NAME


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

    from PySide6.QtWebEngineCore import QWebEngineProfile

    resolved = paths or WhatsAppProfilePaths.default()
    resolved.create()
    profile = QWebEngineProfile(PROFILE_NAME, parent)
    profile.setPersistentStoragePath(str(resolved.storage))
    profile.setCachePath(str(resolved.cache))
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )
    return profile
