"""Persistence operations for authentication and authorization."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.authentication.models import ActivityLog, Permission, Role, User


class UserRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def get_by_username(self, username: str) -> User | None:
        with session_scope(self._session_factory) as session:
            statement = (
                select(User)
                .where(User.username == username)
                .options(selectinload(User.roles).selectinload(Role.permissions))
            )
            return session.scalar(statement)

    def count(self) -> int:
        with session_scope(self._session_factory) as session:
            return session.scalar(select(func.count(User.id))) or 0

    def create(
        self,
        *,
        username: str,
        password_hash: str,
        full_name: str,
        email: str | None,
        role_names: tuple[str, ...],
    ) -> User:
        with session_scope(self._session_factory) as session:
            roles = list(session.scalars(select(Role).where(Role.name.in_(role_names))))
            if len(roles) != len(set(role_names)):
                raise ValueError("One or more requested roles do not exist")
            user = User(
                username=username,
                password_hash=password_hash,
                full_name=full_name,
                email=email,
                roles=roles,
            )
            session.add(user)
            session.flush()
            user_id = user.id
        created = self.get_by_id(user_id)
        if created is None:
            raise RuntimeError("Created user could not be reloaded")
        return created

    def get_by_id(self, user_id: int) -> User | None:
        with session_scope(self._session_factory) as session:
            statement = (
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.roles).selectinload(Role.permissions))
            )
            return session.scalar(statement)

    def update_last_login(self, user_id: int, timestamp: datetime) -> None:
        with session_scope(self._session_factory) as session:
            user = session.get(User, user_id)
            if user is not None:
                user.last_login_at = timestamp


class RoleRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def ensure_permission(self, code: str, description: str) -> Permission:
        with session_scope(self._session_factory) as session:
            permission = session.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, description=description)
                session.add(permission)
                session.flush()
            return permission

    def ensure_role(
        self,
        name: str,
        description: str,
        permission_codes: frozenset[str],
    ) -> Role:
        with session_scope(self._session_factory) as session:
            role = session.scalar(
                select(Role).where(Role.name == name).options(selectinload(Role.permissions))
            )
            permissions = list(
                session.scalars(select(Permission).where(Permission.code.in_(permission_codes)))
            )
            if len(permissions) != len(permission_codes):
                raise ValueError("Role references permissions that do not exist")
            if role is None:
                role = Role(name=name, description=description)
                session.add(role)
            role.description = description
            role.permissions = permissions
            session.flush()
            return role

    def list_names(self) -> frozenset[str]:
        with session_scope(self._session_factory) as session:
            return frozenset(session.scalars(select(Role.name)))


class ActivityRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def record(self, action: str, *, user_id: int | None, details: str = "") -> None:
        with session_scope(self._session_factory) as session:
            session.add(ActivityLog(user_id=user_id, action=action, details=details))

    def list_actions(self) -> list[ActivityLog]:
        with session_scope(self._session_factory) as session:
            return list(session.scalars(select(ActivityLog).order_by(ActivityLog.id)))
