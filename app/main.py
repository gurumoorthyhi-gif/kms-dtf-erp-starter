import sys

from loguru import logger
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from app.core.config import Settings, initialize_directories
from app.core.logging import configure_logging


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("KMS DTF ERP")
        self.resize(1280, 800)
        self.setCentralWidget(QLabel("KMS DTF ERP foundation is ready."))


def main() -> int:
    settings = Settings.load()
    initialize_directories(settings)
    configure_logging(settings)
    logger.info("Starting {}", settings.app_name)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
