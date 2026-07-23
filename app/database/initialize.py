"""Alembic-driven database initialization."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.database.session import resolve_database_url


def upgrade_database(
    database_url: str,
    *,
    base_directory: Path | None = None,
    revision: str = "head",
) -> None:
    """Upgrade the configured database to a reviewed migration revision."""

    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parent / "migrations"),
    )
    resolved_url = resolve_database_url(database_url, base_directory=base_directory)
    config.attributes["database_url"] = resolved_url.render_as_string(hide_password=False)
    config.set_main_option(
        "sqlalchemy.url",
        resolved_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    command.upgrade(config, revision)
