"""Persistent Backblaze settings with secrets kept in the OS credential vault."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SECRET_SERVICE = "KMS DTF ERP Backblaze"


@dataclass(slots=True)
class BackblazeConfiguration:
    endpoint_url: str = ""
    bucket: str = ""
    key_id: str = ""
    google_catalog_enabled: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint_url and self.bucket and self.key_id)


class StorageConfigurationStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> tuple[BackblazeConfiguration, str]:
        data = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        config = BackblazeConfiguration(
            endpoint_url=str(data.get("endpoint_url", "")),
            bucket=str(data.get("bucket", "")),
            key_id=str(data.get("key_id", "")),
            google_catalog_enabled=bool(data.get("google_catalog_enabled", False)),
        )
        try:
            secret = keyring.get_password(SECRET_SERVICE, config.key_id) or ""
        except KeyringError:
            secret = ""
        return config, secret

    def save(self, config: BackblazeConfiguration, application_key: str = "") -> None:
        if not config.is_configured:
            raise ValueError("Endpoint, bucket, and key ID are required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        temporary.replace(self.path)
        if application_key:
            try:
                keyring.set_password(SECRET_SERVICE, config.key_id, application_key)
            except KeyringError as error:
                raise RuntimeError("The Windows credential vault is unavailable") from error

    def clear(self) -> None:
        config, _ = self.load()
        if config.key_id:
            try:
                keyring.delete_password(SECRET_SERVICE, config.key_id)
            except (KeyringError, PasswordDeleteError):
                pass
        self.path.unlink(missing_ok=True)
