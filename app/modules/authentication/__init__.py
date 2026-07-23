"""Authentication and authorization module."""

from app.modules.authentication.current_user import AuthenticatedUser, CurrentUserSession
from app.modules.authentication.models import ActivityLog, Permission, Role, User
from app.modules.authentication.repositories import (
    ActivityRepository,
    RoleRepository,
    UserRepository,
)
from app.modules.authentication.security import (
    MINIMUM_PASSWORD_LENGTH,
    PasswordHasher,
    PasswordPolicyError,
)
from app.modules.authentication.service import (
    AuthenticationError,
    AuthenticationService,
    AuthorizationError,
)

__all__ = [
    "ActivityLog",
    "ActivityRepository",
    "AuthenticatedUser",
    "AuthenticationError",
    "AuthenticationService",
    "AuthorizationError",
    "CurrentUserSession",
    "MINIMUM_PASSWORD_LENGTH",
    "PasswordHasher",
    "PasswordPolicyError",
    "Permission",
    "Role",
    "RoleRepository",
    "User",
    "UserRepository",
]
