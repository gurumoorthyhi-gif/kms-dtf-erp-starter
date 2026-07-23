"""Global handling for otherwise unhandled Python exceptions."""

from __future__ import annotations

import sys
from types import TracebackType

from loguru import logger


def handle_unhandled_exception(
    exception_type: type[BaseException],
    exception: BaseException,
    traceback: TracebackType | None,
) -> None:
    """Log uncaught exceptions while preserving normal interrupt behavior."""

    if issubclass(exception_type, KeyboardInterrupt):
        sys.__excepthook__(exception_type, exception, traceback)
        return

    logger.opt(exception=(exception_type, exception, traceback)).critical(
        "Unhandled application exception"
    )


def install_global_exception_handler() -> None:
    """Install the application exception hook for the current process."""

    sys.excepthook = handle_unhandled_exception
