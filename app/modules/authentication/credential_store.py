"""OS-backed remembered login credentials."""

from dataclasses import dataclass
from typing import Protocol

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "KMS DTF ERP"
LAST_USER_KEY = "__last_username__"


class CredentialStoreProtocol(Protocol):
    def load(self) -> tuple[str, str] | None: ...
    def save(self, username: str, password: str) -> None: ...
    def clear(self) -> None: ...


@dataclass(slots=True)
class WindowsCredentialStore:
    """Store credentials through keyring's Windows Credential Manager backend."""

    service_name: str = SERVICE_NAME

    def load(self) -> tuple[str, str] | None:
        try:
            username = keyring.get_password(self.service_name, LAST_USER_KEY)
            if not username:
                return None
            password = keyring.get_password(self.service_name, username)
            return (username, password) if password else None
        except KeyringError:
            return None

    def save(self, username: str, password: str) -> None:
        normalized = username.strip().casefold()
        if not normalized or not password:
            raise ValueError("Username and password are required")
        try:
            previous = keyring.get_password(self.service_name, LAST_USER_KEY)
            if previous and previous != normalized:
                keyring.delete_password(self.service_name, previous)
            keyring.set_password(self.service_name, normalized, password)
            keyring.set_password(self.service_name, LAST_USER_KEY, normalized)
        except KeyringError as error:
            raise RuntimeError("Windows Credential Manager is unavailable") from error

    def clear(self) -> None:
        try:
            username = keyring.get_password(self.service_name, LAST_USER_KEY)
            if username:
                keyring.delete_password(self.service_name, username)
            keyring.delete_password(self.service_name, LAST_USER_KEY)
        except KeyringError:
            return
