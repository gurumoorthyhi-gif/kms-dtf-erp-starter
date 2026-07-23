"""Application exception handling."""

from app.core.exceptions.handler import (
    handle_unhandled_exception,
    install_global_exception_handler,
)

__all__ = ["handle_unhandled_exception", "install_global_exception_handler"]
