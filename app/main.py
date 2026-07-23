import sys

from loguru import logger
from PySide6.QtWidgets import QApplication

from app.core.config import Settings, initialize_directories
from app.core.exceptions import install_global_exception_handler
from app.core.logging import configure_logging
from app.database import (
    check_database_health,
    create_database_engine,
    create_session_factory,
    upgrade_database,
)
from app.modules.authentication import (
    ActivityRepository,
    AuthenticationService,
    CurrentUserSession,
    PasswordHasher,
    RoleRepository,
    UserRepository,
)
from app.modules.customers import CustomerRepository, CustomerService
from app.modules.dashboard import DashboardRepository, DashboardService
from app.modules.products import ProductRepository, ProductService
from app.ui.application import MainWindow


def main() -> int:
    install_global_exception_handler()
    settings = Settings.load()
    paths = initialize_directories(settings)
    configure_logging(settings, paths)
    logger.info("Starting {}", settings.app_name)

    upgrade_database(settings.database_url, base_directory=paths.base_directory)
    engine = create_database_engine(
        settings.database_url,
        echo=settings.app_debug,
        base_directory=paths.base_directory,
    )
    if not check_database_health(engine):
        logger.error("Database is unavailable; startup will continue in a degraded state")
    session_factory = create_session_factory(engine)
    authentication_service = AuthenticationService(
        UserRepository(session_factory),
        RoleRepository(session_factory),
        ActivityRepository(session_factory),
        PasswordHasher(),
        CurrentUserSession(),
    )
    authentication_service.seed_roles_and_permissions()
    dashboard_service = DashboardService(
        DashboardRepository(session_factory),
        authentication_service,
    )
    customer_service = CustomerService(
        CustomerRepository(session_factory),
        authentication_service,
    )
    product_service = ProductService(
        ProductRepository(session_factory),
        authentication_service,
    )

    app = QApplication(sys.argv)
    window = MainWindow(
        authentication_service,
        dashboard_service,
        customer_service=customer_service,
        product_service=product_service,
    )
    window.show()
    try:
        return app.exec()
    finally:
        engine.dispose()
