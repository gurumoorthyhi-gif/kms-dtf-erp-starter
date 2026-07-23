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
from app.ui.pages import LoginPage

ADMIN_PASSWORD = "Correct-Horse-42"


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
    page = LoginPage(authentication_service)
    qtbot.addWidget(page)
    page.username_input.setText("admin")
    page.password_input.setText("wrong-password")

    qtbot.mouseClick(page.login_button, Qt.MouseButton.LeftButton)

    assert page.error_label.isVisible() is False or page.error_label.text()
    assert page.error_label.text() == "Invalid username or password"
    assert page.password_input.text() == ""


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
