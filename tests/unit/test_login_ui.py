from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from app.database import Base, create_database_engine, create_session_factory
from app.modules.authentication import (
    ActivityRepository,
    AuthenticationService,
    CurrentUserSession,
    PasswordHasher,
    RoleRepository,
    UserRepository,
)
from app.modules.dashboard import DashboardService, EmptyDashboardRepository
from app.ui.application import MainWindow
from app.ui.pages import CreateAdministratorDialog, LoginPage

ADMIN_PASSWORD = "Correct-Horse-42"


class MemoryCredentialStore:
    def __init__(self, value=None) -> None:
        self.value = value

    def load(self):
        return self.value

    def save(self, username: str, password: str) -> None:
        self.value = (username.strip().casefold(), password)

    def clear(self) -> None:
        self.value = None


@pytest.fixture
def authentication_service(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'login-ui.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    service = AuthenticationService(
        UserRepository(factory),
        RoleRepository(factory),
        ActivityRepository(factory),
        PasswordHasher(),
        CurrentUserSession(),
    )
    service.create_administrator(
        username="admin",
        password=ADMIN_PASSWORD,
        full_name="System Administrator",
    )
    yield service
    engine.dispose()


def test_login_page_rejects_invalid_credentials(qtbot, authentication_service) -> None:
    page = LoginPage(authentication_service, MemoryCredentialStore())
    qtbot.addWidget(page)
    page.username_input.setText("admin")
    page.password_input.setText("wrong-password")

    qtbot.mouseClick(page.login_button, Qt.MouseButton.LeftButton)

    assert page.error_label.isVisible() is False or page.error_label.text()
    assert page.error_label.text() == "Invalid username or password"
    assert page.password_input.text() == ""


def test_login_page_remembers_and_restores_credentials(qtbot, authentication_service) -> None:
    store = MemoryCredentialStore()
    page = LoginPage(authentication_service, store)
    qtbot.addWidget(page)
    page.username_input.setText("ADMIN")
    page.password_input.setText(ADMIN_PASSWORD)
    page.remember_me.setChecked(True)

    qtbot.mouseClick(page.login_button, Qt.MouseButton.LeftButton)
    page.reset()

    assert store.value == ("admin", ADMIN_PASSWORD)
    assert page.username_input.text() == "admin"
    assert page.password_input.text() == ADMIN_PASSWORD
    assert page.remember_me.isChecked()


def test_password_eye_toggles_login_password_visibility(qtbot, authentication_service) -> None:
    page = LoginPage(authentication_service, MemoryCredentialStore())
    qtbot.addWidget(page)
    page.password_input.setText(ADMIN_PASSWORD)

    page.password_visibility_action.trigger()
    assert page.password_input.echoMode() == page.password_input.EchoMode.Normal
    assert page.password_input.text() == ADMIN_PASSWORD

    page.password_visibility_action.trigger()
    assert page.password_input.echoMode() == page.password_input.EchoMode.Password


def test_main_window_login_and_logout_flow(qtbot, authentication_service) -> None:
    dashboard_service = DashboardService(
        EmptyDashboardRepository(),
        authentication_service,
    )
    window = MainWindow(authentication_service, dashboard_service)
    qtbot.addWidget(window)
    window.show()

    assert window.router.current_page_name == "login"
    assert window.sidebar.isHidden()
    assert window.login_page is not None
    assert window.dashboard_page.error_label.isHidden()

    window.login_page.username_input.setText("admin")
    window.login_page.password_input.setText(ADMIN_PASSWORD)
    window.login_page.submit()

    assert window.router.current_page_name == "dashboard"
    assert window.sidebar.isVisible()
    assert window.dashboard_page.error_label.isHidden()
    assert authentication_service.current_session.is_authenticated is True

    window.logout()

    assert window.router.current_page_name == "login"
    assert authentication_service.current_session.is_authenticated is False


def test_create_administrator_dialog_collects_admin_details(qtbot, tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'first-run.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    service = AuthenticationService(
        UserRepository(factory),
        RoleRepository(factory),
        ActivityRepository(factory),
        PasswordHasher(),
        CurrentUserSession(),
    )
    dialog = CreateAdministratorDialog(service)
    qtbot.addWidget(dialog)
    dialog.full_name.setText("KMS Owner")
    dialog.username.setText("owner")
    dialog.email.setText("owner@example.com")
    dialog.password.setText(ADMIN_PASSWORD)
    dialog.confirm_password.setText(ADMIN_PASSWORD)

    dialog.password_visibility_action.trigger()
    dialog.confirm_visibility_action.trigger()
    assert dialog.password.echoMode() == dialog.password.EchoMode.Normal
    assert dialog.confirm_password.echoMode() == dialog.confirm_password.EchoMode.Normal

    dialog.create_account()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert service.authenticate("owner", ADMIN_PASSWORD).full_name == "KMS Owner"
    engine.dispose()
