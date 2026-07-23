from pathlib import Path

from loguru import logger

from app.core.config import Settings, initialize_directories
from app.core.logging import configure_logging


def test_configure_logging_writes_to_rotating_log(tmp_path: Path) -> None:
    settings = Settings(log_directory=tmp_path / "logs")
    initialize_directories(settings)

    log_path = configure_logging(settings)
    logger.info("configuration test message")
    logger.complete()

    assert log_path.is_file()
    assert "configuration test message" in log_path.read_text(encoding="utf-8")
