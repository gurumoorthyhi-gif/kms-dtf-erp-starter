"""Database connectivity checks."""

from loguru import logger
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError


def check_database_health(engine: Engine) -> bool:
    """Return whether the database accepts a minimal query."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return False
    return True
