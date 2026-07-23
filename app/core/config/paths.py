"""Application path resolution and runtime directory management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config.settings import Settings


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    """Absolute paths used by local application services."""

    base_directory: Path
    log_directory: Path
    local_storage_directory: Path
    artwork_directory: Path
    export_directory: Path
    backup_directory: Path

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        base_directory: Path | None = None,
    ) -> ApplicationPaths:
        """Resolve configured paths against one explicit application directory."""

        base = (base_directory or Path.cwd()).resolve()

        def resolve(path: Path) -> Path:
            return path.resolve() if path.is_absolute() else (base / path).resolve()

        return cls(
            base_directory=base,
            log_directory=resolve(settings.log_directory),
            local_storage_directory=resolve(settings.local_storage_directory),
            artwork_directory=resolve(settings.artwork_directory),
            export_directory=resolve(settings.export_directory),
            backup_directory=resolve(settings.backup_directory),
        )

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

    def create_runtime_directories(self) -> None:
        """Create the complete local runtime directory tree."""

        for directory in self.runtime_directories:
            directory.mkdir(parents=True, exist_ok=True)
