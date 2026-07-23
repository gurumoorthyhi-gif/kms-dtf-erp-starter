"""In-memory current-user session."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Minimal identity exposed outside the persistence layer."""

    id: int
    username: str
    full_name: str
    roles: frozenset[str]
    permissions: frozenset[str]


class CurrentUserSession:
    """Own the authenticated identity for one desktop process."""

    def __init__(self) -> None:
        self._user: AuthenticatedUser | None = None

    @property
    def user(self) -> AuthenticatedUser | None:
        return self._user

    @property
    def is_authenticated(self) -> bool:
        return self._user is not None

    def login(self, user: AuthenticatedUser) -> None:
        self._user = user

    def logout(self) -> None:
        self._user = None
