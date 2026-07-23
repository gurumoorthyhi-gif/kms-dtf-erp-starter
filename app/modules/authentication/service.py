"""Authentication and authorization use cases."""

from __future__ import annotations

from app.modules.authentication.current_user import AuthenticatedUser, CurrentUserSession
from app.modules.authentication.models import User, utc_now
from app.modules.authentication.permissions import PERMISSIONS, ROLE_PERMISSIONS
from app.modules.authentication.repositories import (
    ActivityRepository,
    RoleRepository,
    UserRepository,
)
from app.modules.authentication.security import PasswordHasher


class AuthenticationError(ValueError):
    """Raised when supplied credentials cannot be accepted."""


class AuthorizationError(PermissionError):
    """Raised when the current identity lacks a required permission."""


class AuthenticationService:
    """Coordinate secure login, logout, permissions, and administrator setup."""

    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        activities: ActivityRepository,
        password_hasher: PasswordHasher,
        current_session: CurrentUserSession,
    ) -> None:
        self._users = users
        self._roles = roles
        self._activities = activities
        self._password_hasher = password_hasher
        self.current_session = current_session

    def seed_roles_and_permissions(self) -> None:
        for code, description in PERMISSIONS.items():
            self._roles.ensure_permission(code, description)
        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            self._roles.ensure_role(
                role_name,
                f"Built-in {role_name} role",
                permission_codes,
            )

    def create_administrator(
        self,
        *,
        username: str,
        password: str,
        full_name: str,
        email: str | None = None,
    ) -> AuthenticatedUser:
        normalized_username = username.strip().casefold()
        if not normalized_username:
            raise ValueError("Username is required")
        if self._users.get_by_username(normalized_username) is not None:
            raise ValueError("Username already exists")

        self.seed_roles_and_permissions()
        user = self._users.create(
            username=normalized_username,
            password_hash=self._password_hasher.hash(password),
            full_name=full_name.strip() or normalized_username,
            email=email.strip().casefold() if email else None,
            role_names=("Administrator",),
        )
        self._activities.record(
            "administrator.created",
            user_id=user.id,
            details=f"Administrator account created for {normalized_username}",
        )
        return self._to_authenticated_user(user)

    def authenticate(self, username: str, password: str) -> AuthenticatedUser:
        normalized_username = username.strip().casefold()
        user = self._users.get_by_username(normalized_username)
        if (
            user is None
            or not user.is_active
            or not self._password_hasher.verify(password, user.password_hash)
        ):
            self._activities.record(
                "login.failed",
                user_id=user.id if user is not None else None,
                details=f"Rejected login for {normalized_username}",
            )
            raise AuthenticationError("Invalid username or password")

        authenticated_user = self._to_authenticated_user(user)
        self.current_session.login(authenticated_user)
        self._users.update_last_login(user.id, utc_now())
        self._activities.record(
            "login.succeeded",
            user_id=user.id,
            details=f"Login accepted for {normalized_username}",
        )
        return authenticated_user

    def logout(self) -> None:
        user = self.current_session.user
        if user is not None:
            self._activities.record(
                "logout",
                user_id=user.id,
                details=f"Logout for {user.username}",
            )
        self.current_session.logout()

    def require_permission(self, permission_code: str) -> None:
        user = self.current_session.user
        if user is None or permission_code not in user.permissions:
            self._activities.record(
                "permission.denied",
                user_id=user.id if user is not None else None,
                details=f"Permission denied: {permission_code}",
            )
            raise AuthorizationError(f"Permission required: {permission_code}")

    @staticmethod
    def _to_authenticated_user(user: User) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            roles=frozenset(role.name for role in user.roles),
            permissions=frozenset(
                permission.code for role in user.roles for permission in role.permissions
            ),
        )
