from pathlib import Path

from app.core.config import ApplicationPaths, Settings, initialize_directories


def test_settings_load_dotenv_with_environment_override(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_NAME=Configured ERP\nAPP_DEBUG=false\nLOG_LEVEL=WARNING\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_DEBUG", "true")

    settings = Settings.load(env_file)

    assert settings.app_name == "Configured ERP"
    assert settings.app_debug is True
    assert settings.log_level == "WARNING"


def test_initialize_directories_creates_runtime_tree(tmp_path: Path) -> None:
    settings = Settings(
        log_directory=tmp_path / "logs",
        local_storage_directory=tmp_path / "data",
        artwork_directory=tmp_path / "data" / "artwork",
        export_directory=tmp_path / "exports",
        backup_directory=tmp_path / "backups",
    )

    paths = initialize_directories(settings, base_directory=tmp_path)

    assert all(path.is_dir() for path in settings.runtime_directories)
    assert all(path.is_absolute() for path in paths.runtime_directories)


def test_application_paths_resolve_relative_configuration(tmp_path: Path) -> None:
    settings = Settings(
        log_directory=Path("runtime/logs"),
        local_storage_directory=Path("runtime/data"),
        artwork_directory=Path("runtime/data/artwork"),
        export_directory=Path("runtime/exports"),
        backup_directory=Path("runtime/backups"),
    )

    paths = ApplicationPaths.from_settings(settings, base_directory=tmp_path)

    assert paths.base_directory == tmp_path.resolve()
    assert paths.log_directory == (tmp_path / "runtime" / "logs").resolve()
    assert paths.artwork_directory == (tmp_path / "runtime" / "data" / "artwork").resolve()
