"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.core.config.paths import ApplicationPaths


class Settings(BaseModel):
    """Runtime settings with safe development defaults."""

    model_config = ConfigDict(frozen=True)

    app_name: str = "KMS DTF ERP"
    app_env: str = "development"
    app_debug: bool = False
    database_url: str = "sqlite:///local_data/kms_dtf_erp.db"
    log_level: str = "INFO"
    log_directory: Path = Path("logs")
    local_storage_directory: Path = Path("local_data")
    artwork_directory: Path = Path("local_data/artwork")
    export_directory: Path = Path("exports")
    backup_directory: Path = Path("backups")
    cloud_provider: str = ""
    cloud_bucket: str = ""
    cloud_access_key: str = ""
    cloud_secret_key: str = ""
    whatsapp_provider: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    email_provider: str = ""
    email_address: str = ""
    email_app_password: str = ""
    ai_engine_url: str = "http://127.0.0.1:8001"
    ai_engine_api_key: str = ""

    @classmethod
    def load(cls, env_file: str | Path | None = ".env") -> Settings:
        """Load an optional dotenv file, with process environment taking precedence."""

        values: dict[str, Any] = {}
        env_to_field = {field_name.upper(): field_name for field_name in cls.model_fields}
        if env_file is not None:
            for key, value in dotenv_values(env_file).items():
                field_name = env_to_field.get(key)
                if field_name is not None and value is not None:
                    values[field_name] = value

        for env_name, field_name in env_to_field.items():
            if env_name in os.environ:
                values[field_name] = os.environ[env_name]

        return cls.model_validate(values)

    @property
    def runtime_directories(self) -> tuple[Path, ...]:
        """Directories that must exist before application services start."""

        return (
            self.log_directory,
            self.local_storage_directory,
            self.artwork_directory,
            self.export_directory,
            self.backup_directory,
        )


def initialize_directories(
    settings: Settings,
    *,
    base_directory: Path | None = None,
) -> ApplicationPaths:
    """Resolve and create all configured runtime directories."""

    from app.core.config.paths import ApplicationPaths

    paths = ApplicationPaths.from_settings(settings, base_directory=base_directory)
    paths.create_runtime_directories()
    return paths
