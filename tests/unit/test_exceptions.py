import sys

from loguru import logger

from app.core.exceptions import (
    handle_unhandled_exception,
    install_global_exception_handler,
)


def test_global_exception_handler_is_installed(monkeypatch) -> None:
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)

    install_global_exception_handler()

    assert sys.excepthook is handle_unhandled_exception


def test_unhandled_exception_is_logged() -> None:
    messages: list[str] = []
    sink_id = logger.add(messages.append, format="{message}")
    exception = RuntimeError("unexpected failure")

    handle_unhandled_exception(RuntimeError, exception, exception.__traceback__)

    logger.remove(sink_id)
    assert any("Unhandled application exception" in message for message in messages)
