from pathlib import Path

import pytest

from app.database import Base, create_database_engine, create_session_factory
from app.modules.authentication import (
    ActivityRepository,
    AuthenticationError,
    AuthenticationService,
    AuthorizationError,
    CurrentUserSession,
    PasswordHasher,
    PasswordPolicyError,
    RoleRepository,
    UserRepository,
)

ADMIN_PASSWORD = "Correct-Horse-42"


@pytest.fixture
def authentication_context(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'authentication.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    users = UserRepository(factory)
    roles = RoleRepository(factory)
    activities = ActivityRepository(factory)
    service = AuthenticationService(
        users,
        roles,
        activities,
        PasswordHasher(),
        CurrentUserSession(),
    )
    yield service, users, roles, activities
    engine.dispose()


def test_password_hasher_never_stores_plaintext() -> None:
    hasher = PasswordHasher()

    encoded = hasher.hash(ADMIN_PASSWORD)

    assert ADMIN_PASSWORD not in encoded
    assert encoded.startswith("scrypt$")
    assert hasher.verify(ADMIN_PASSWORD, encoded) is True
    assert hasher.verify("wrong-password", encoded) is False


def test_password_policy_rejects_short_password() -> None:
    with pytest.raises(PasswordPolicyError):
        PasswordHasher().hash("too-short")


def test_password_hasher_rejects_malformed_or_untrusted_hashes() -> None:
    hasher = PasswordHasher()

    assert hasher.verify(ADMIN_PASSWORD, "not-a-valid-hash") is False
    assert hasher.verify(ADMIN_PASSWORD, "scrypt$999999$8$1$c2FsdA==$aGFzaA==") is False


def test_administrator_creation_and_valid_login(authentication_context) -> None:
    service, users, _, activities = authentication_context

    created = service.create_administrator(
        username="Admin",
        password=ADMIN_PASSWORD,
        full_name="System Administrator",
    )
    authenticated = service.authenticate("ADMIN", ADMIN_PASSWORD)
    stored = users.get_by_username("admin")

    assert created.username == "admin"
    assert "Administrator" in created.roles
    assert authenticated == service.current_session.user
    assert "users.manage" in authenticated.permissions
    assert stored is not None
    assert stored.password_hash != ADMIN_PASSWORD
    assert stored.last_login_at is not None
    assert [activity.action for activity in activities.list_actions()] == [
        "administrator.created",
        "login.succeeded",
    ]


def test_invalid_login_is_rejected_and_password_is_not_logged(authentication_context) -> None:
    service, _, _, activities = authentication_context
    service.create_administrator(
        username="admin",
        password=ADMIN_PASSWORD,
        full_name="Administrator",
    )

    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        service.authenticate("admin", "definitely-wrong")

    assert service.current_session.is_authenticated is False
    failure = activities.list_actions()[-1]
    assert failure.action == "login.failed"
    assert "definitely-wrong" not in failure.details


def test_initial_administrator_can_only_be_created_once(authentication_context) -> None:
    service, _, _, _ = authentication_context
    assert service.can_create_initial_administrator() is True

    created = service.create_initial_administrator(
        username="owner",
        password=ADMIN_PASSWORD,
        full_name="Business Owner",
        email="owner@example.com",
    )

    assert created.full_name == "Business Owner"
    assert service.can_create_initial_administrator() is False
    with pytest.raises(AuthorizationError, match="already exists"):
        service.create_initial_administrator(
            username="another",
            password=ADMIN_PASSWORD,
            full_name="Another Administrator",
        )


def test_logout_and_permissions_are_enforced(authentication_context) -> None:
    service, _, _, activities = authentication_context
    service.create_administrator(
        username="admin",
        password=ADMIN_PASSWORD,
        full_name="Administrator",
    )
    service.authenticate("admin", ADMIN_PASSWORD)

    service.require_permission("users.manage")
    with pytest.raises(AuthorizationError):
        service.require_permission("unknown.manage")
    service.logout()

    assert service.current_session.is_authenticated is False
    assert [activity.action for activity in activities.list_actions()][-2:] == [
        "permission.denied",
        "logout",
    ]


def test_all_initial_roles_are_seeded(authentication_context) -> None:
    service, _, roles, _ = authentication_context
    service.seed_roles_and_permissions()
    administrator = service.create_administrator(
        username="admin",
        password=ADMIN_PASSWORD,
        full_name="Administrator",
    )

    assert administrator.roles == frozenset({"Administrator"})
    assert roles.list_names() == frozenset(
        {
            "Administrator",
            "Manager",
            "Designer",
            "Production Operator",
            "Accountant",
            "Packing Staff",
            "Dispatch Staff",
            "Viewer",
        }
    )
