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
from app.modules.ai_engine import (
    AIEngineClient,
    AIJobManager,
    AIResultHandler,
)
from app.modules.artwork import (
    ArtworkRepository,
    ArtworkService,
    ArtworkStorage,
    PreviewService,
)
from app.modules.artwork_studio import (
    ArtworkStudioService,
    ImageInspector,
    ImageTransformer,
    ThumbnailCache,
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
from app.modules.gang_sheets import GangSheetRepository, GangSheetService
from app.modules.inventory import (
    InventoryRepository,
    InventoryService,
    PurchaseRepository,
    PurchaseService,
)
from app.modules.orders import OrderRepository, OrderService
from app.modules.production import ProductionRepository, ProductionService
from app.modules.products import ProductRepository, ProductService
from app.modules.sales import SalesRepository, SalesService
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
    order_service = OrderService(
        OrderRepository(session_factory),
        product_service,
        authentication_service,
    )
    artwork_service = ArtworkService(
        ArtworkRepository(session_factory),
        ArtworkStorage(paths.artwork_directory, PreviewService()),
        authentication_service,
    )
    artwork_studio_service = ArtworkStudioService(
        artwork_service,
        ImageTransformer(),
        ImageInspector(),
        ThumbnailCache(paths.local_storage_directory / "thumbnail_cache"),
    )
    ai_job_manager = AIJobManager(
        AIEngineClient(settings.ai_engine_url, settings.ai_engine_api_key),
        AIResultHandler(artwork_service),
        paths.local_storage_directory / "ai_results",
    )
    gang_sheet_service = GangSheetService(
        GangSheetRepository(session_factory),
        artwork_service,
        paths.export_directory,
        authentication_service,
    )
    production_service = ProductionService(
        ProductionRepository(session_factory),
        authentication_service,
    )
    inventory_service = InventoryService(
        InventoryRepository(session_factory),
        authentication_service,
    )
    purchase_service = PurchaseService(
        PurchaseRepository(session_factory),
        authentication_service,
    )
    sales_service = SalesService(
        SalesRepository(session_factory),
        authentication_service,
    )

    app = QApplication(sys.argv)
    window = MainWindow(
        authentication_service,
        dashboard_service,
        customer_service=customer_service,
        product_service=product_service,
        order_service=order_service,
        artwork_service=artwork_service,
        artwork_studio_service=artwork_studio_service,
        ai_job_manager=ai_job_manager,
        gang_sheet_service=gang_sheet_service,
        production_service=production_service,
        inventory_service=inventory_service,
        purchase_service=purchase_service,
        sales_service=sales_service,
    )
    window.show()
    try:
        return app.exec()
    finally:
        ai_job_manager.close()
        engine.dispose()
