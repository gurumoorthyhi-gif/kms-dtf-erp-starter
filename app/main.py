import sys

from loguru import logger
from PySide6.QtWidgets import QApplication

from app.core.config import Settings, initialize_directories
from app.core.exceptions import install_global_exception_handler
from app.core.logging import configure_logging
from app.database import check_database_health, create_database_engine
from app.ui.application import MainWindow


def main() -> int:
    install_global_exception_handler()
    settings = Settings.load()
    paths = initialize_directories(settings)
    configure_logging(settings, paths)
    logger.info("Starting {}", settings.app_name)

    engine = create_database_engine(
        settings.database_url,
        echo=settings.app_debug,
        base_directory=paths.base_directory,
    )
    if not check_database_health(engine):
        logger.error("Database is unavailable; startup will continue in a degraded state")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    try:
        return app.exec()
    finally:
        engine.dispose()
