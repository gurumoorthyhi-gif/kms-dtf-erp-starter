import ctypes
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
from app.modules.artwork import (
    ArtworkRepository,
    ArtworkService,
    ArtworkStorage,
    PreviewService,
)
from app.modules.authentication import (
    ActivityRepository,
    AuthenticationService,
    CurrentUserSession,
    PasswordHasher,
    RoleRepository,
    UserRepository,
)
from app.modules.cloud_storage import (
    CloudStorageService,
    LocalStorageProvider,
    S3CompatibleProvider,
    StorageConfigurationStore,
)
from app.modules.communications import CommunicationService, UnconfiguredProvider
from app.modules.customers import (
    CustomerRepository,
    CustomerService,
    CustomerSyncError,
    GoogleCustomerSheetSync,
)
from app.modules.dashboard import DashboardRepository, DashboardService
from app.modules.gang_sheets import GangSheetRepository, GangSheetService
from app.modules.inventory import (
    InventoryRepository,
    InventoryService,
    PurchaseRepository,
    PurchaseService,
)
from app.modules.operations import AuditService, BackupService, ReportService
from app.modules.orders import OrderRepository, OrderService
from app.modules.products import ProductRepository, ProductService
from app.modules.sales import SalesRepository, SalesService
from app.modules.shipping import DispatchService, PackingService, ShippingRepository


def __getattr__(name: str):
    """Preserve the public MainWindow export without eagerly importing the UI."""

    if name == "MainWindow":
        from app.ui.application import MainWindow

        return MainWindow
    raise AttributeError(name)


def _set_windows_app_id() -> None:
    """Give Windows a stable identity for taskbar icon grouping."""

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "KMS.DTF.ERP"
        )


def main() -> int:
    # Heavy image/UI imports are deferred until launch. Import profiling showed these
    # dominated non-GUI module startup and they are unnecessary for CLI tooling.
    from app.modules.ai_engine import AIEngineClient, AIJobManager, AIResultHandler
    from app.ui.application import MainWindow
    from app.ui.branding import application_icon

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
    development_user = (
        authentication_service.start_development_session()
        if settings.app_env.casefold() == "development"
        else None
    )
    dashboard_service = DashboardService(
        DashboardRepository(session_factory),
        authentication_service,
    )
    customer_repository = CustomerRepository(session_factory)
    customer_sheet_sync = GoogleCustomerSheetSync(
        customer_repository,
        credentials_path=settings.google_oauth_credentials,
        token_path=settings.google_oauth_token,
        state_path=settings.google_drive_state,
    )
    customer_service = CustomerService(
        customer_repository,
        authentication_service,
        customer_sheet_sync,
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
    storage_configuration_store = StorageConfigurationStore(
        paths.local_storage_directory / "storage_settings.json"
    )
    storage_configuration, storage_secret = storage_configuration_store.load()
    storage_provider = LocalStorageProvider(
        paths.local_storage_directory / "cloud_provider"
    )
    if storage_configuration.is_configured and storage_secret:
        try:
            storage_provider = S3CompatibleProvider.for_backblaze(
                endpoint_url=storage_configuration.endpoint_url,
                key_id=storage_configuration.key_id,
                application_key=storage_secret,
                bucket=storage_configuration.bucket,
            )
        except Exception:
            logger.exception("Backblaze configuration could not be loaded; using local queue")
    cloud_service = CloudStorageService(
        session_factory,
        storage_provider,
        paths.local_storage_directory / "cloud_cache",
    )
    if storage_configuration.google_catalog_enabled and customer_sheet_sync.is_connected:
        cloud_service.set_upload_completed_callback(
            customer_sheet_sync.create_storage_catalog_entry
        )
    whatsapp_service = CommunicationService(
        session_factory,
        "whatsapp",
        UnconfiguredProvider(),
        paths.local_storage_directory / "communications" / "whatsapp",
        authentication_service,
    )
    email_service = CommunicationService(
        session_factory,
        "email",
        UnconfiguredProvider(),
        paths.local_storage_directory / "communications" / "email",
        authentication_service,
    )
    shipping_repository = ShippingRepository(session_factory)
    packing_service = PackingService(shipping_repository, authentication_service)
    dispatch_service = DispatchService(shipping_repository, authentication_service)
    report_service = ReportService(session_factory)
    backup_service = BackupService(engine, session_factory, paths.backup_directory, cloud_service)
    audit_service = AuditService(session_factory)

    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setWindowIcon(application_icon())
    if customer_sheet_sync is not None and customer_sheet_sync.is_connected:
        try:
            customer_service.sync_customer_sheet()
        except CustomerSyncError:
            logger.exception("Initial Google customer-sheet synchronization failed")
    window = MainWindow(
        authentication_service,
        dashboard_service,
        initial_user=development_user,
        customer_service=customer_service,
        product_service=product_service,
        order_service=order_service,
        artwork_service=artwork_service,
        ai_job_manager=ai_job_manager,
        gang_sheet_service=gang_sheet_service,
        inventory_service=inventory_service,
        purchase_service=purchase_service,
        sales_service=sales_service,
        packing_service=packing_service,
        dispatch_service=dispatch_service,
        cloud_storage_service=cloud_service,
        whatsapp_service=whatsapp_service,
        email_service=email_service,
        report_service=report_service,
        backup_service=backup_service,
        audit_service=audit_service,
        storage_configuration_store=storage_configuration_store,
        google_sync=customer_sheet_sync,
    )
    window.showMaximized()
    try:
        return app.exec()
    finally:
        ai_job_manager.close()
        engine.dispose()
