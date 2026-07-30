from pathlib import Path

from app.modules.cloud_storage.configuration import (
    BackblazeConfiguration,
    StorageConfigurationStore,
)


def test_storage_configuration_keeps_secret_out_of_json(tmp_path: Path, monkeypatch) -> None:
    secrets = {}
    monkeypatch.setattr(
        "app.modules.cloud_storage.configuration.keyring.set_password",
        lambda service, username, password: secrets.__setitem__((service, username), password),
    )
    monkeypatch.setattr(
        "app.modules.cloud_storage.configuration.keyring.get_password",
        lambda service, username: secrets.get((service, username)),
    )
    path = tmp_path / "storage.json"
    store = StorageConfigurationStore(path)
    config = BackblazeConfiguration(
        endpoint_url="https://s3.example",
        bucket="private",
        key_id="key-id",
        google_catalog_enabled=True,
    )

    store.save(config, "super-secret")
    loaded, secret = store.load()

    assert loaded == config
    assert secret == "super-secret"
    assert "super-secret" not in path.read_text(encoding="utf-8")
