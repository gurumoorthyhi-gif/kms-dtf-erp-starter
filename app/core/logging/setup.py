"""Application logging configuration."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.core.config import ApplicationPaths, Settings


def configure_logging(
    settings: Settings,
    paths: ApplicationPaths | None = None,
) -> Path:
    """Configure console and rotating file logs, returning the active log path."""

    log_directory = paths.log_directory if paths is not None else settings.log_directory
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / "kms-dtf-erp.log"
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        colorize=settings.app_debug,
    )
    logger.add(
        log_path,
        level=settings.log_level.upper(),
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
        enqueue=True,
    )
    return log_path
