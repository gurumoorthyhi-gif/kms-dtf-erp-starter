from io import BytesIO
from pathlib import Path

from app.database import Base, create_database_engine, create_session_factory
from app.modules.cloud_storage import (
    CloudStorageService,
    LocalStorageProvider,
    S3CompatibleProvider,
)


class InterruptibleProvider:
    def __init__(self, online: bool = False, failures: int = 0) -> None:
        self.online, self.failures, self.objects = online, failures, {}

    def is_online(self) -> bool:
        return self.online

    def upload(self, key, source, progress=None):
        if self.failures:
            self.failures -= 1
            raise OSError("interrupted")
        self.objects[key] = source.read()

    def download(self, key, destination, progress=None):
        destination.write(self.objects[key])

    def signed_download_url(self, key, expires_in=900):
        return f"https://files.example/{key}?expires={expires_in}"


def make_service(tmp_path: Path, provider):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'cloud.db'}")
    Base.metadata.create_all(engine)
    service = CloudStorageService(create_session_factory(engine), provider, tmp_path / "cache")
    return engine, service


def test_offline_upload_is_cached_and_synchronized_later(tmp_path: Path) -> None:
    provider = InterruptibleProvider()
    engine, service = make_service(tmp_path, provider)
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"invoice")

    queued = service.queue_upload(source, "invoices/")
    source.unlink()
    provider.online = True

    assert queued.transfer_state == "queued"
    assert service.synchronize() == 1
    assert service.get(queued.id).transfer_state == "synced"
    assert provider.objects[queued.object_key] == b"invoice"
    engine.dispose()


def test_interrupted_upload_retries_without_losing_cache(tmp_path: Path) -> None:
    provider = InterruptibleProvider(True, failures=1)
    engine, service = make_service(tmp_path, provider)
    source = tmp_path / "art.png"
    source.write_bytes(b"pixels")

    failed = service.queue_upload(source, "artwork/original/")
    assert failed.transfer_state == "failed"
    assert failed.retry_count == 1
    assert Path(failed.local_path).read_bytes() == b"pixels"

    assert service.synchronize() == 1
    assert service.get(failed.id).transfer_state == "synced"
    engine.dispose()


def test_download_uses_object_key_and_atomic_partial_file(tmp_path: Path) -> None:
    provider = InterruptibleProvider(True)
    engine, service = make_service(tmp_path, provider)
    source = tmp_path / "dispatch.txt"
    source.write_bytes(b"dispatch")
    record = service.queue_upload(source, "dispatch/")

    destination = service.download(record.id, tmp_path / "downloads" / "copy.txt")

    assert destination.read_bytes() == b"dispatch"
    assert not destination.with_suffix(".txt.part").exists()
    engine.dispose()


def test_access_url_is_available_only_after_upload(tmp_path: Path) -> None:
    provider = InterruptibleProvider(True)
    engine, service = make_service(tmp_path, provider)
    source = tmp_path / "receipt.pdf"
    source.write_bytes(b"receipt")
    record = service.queue_upload(source, "invoices/")

    assert service.access_url(record.id, expires_in=300).endswith("?expires=300")
    engine.dispose()


def test_google_catalog_failure_does_not_mark_backblaze_upload_failed(tmp_path: Path) -> None:
    provider = InterruptibleProvider(True)
    engine, service = make_service(tmp_path, provider)
    service.set_upload_completed_callback(
        lambda _record: (_ for _ in ()).throw(OSError("Google unavailable"))
    )
    source = tmp_path / "design.png"
    source.write_bytes(b"design")

    record = service.queue_upload(source, "artwork/original/")

    saved = service.get(record.id)
    assert saved.transfer_state == "synced"
    assert "Google Drive catalog pending" in saved.last_error
    assert provider.objects[record.object_key] == b"design"
    engine.dispose()


def test_nested_customer_prefix_and_folder_markers_are_supported(tmp_path: Path) -> None:
    provider = InterruptibleProvider(True)
    engine, service = make_service(tmp_path, provider)
    prefix = "customers/CO0001 - KMS - TIRUPUR/2026-07-28/design"

    marker = service.ensure_folder(prefix)

    assert marker.object_key == f"{prefix}/.keep"
    assert marker.transfer_state == "synced"
    assert service.list_prefix(prefix) == []
    assert service.list_prefix(prefix, include_markers=True)[0].id == marker.id
    engine.dispose()


def test_local_and_s3_compatible_providers(tmp_path: Path) -> None:
    local = LocalStorageProvider(tmp_path / "objects")
    local.upload("orders/1/file.txt", BytesIO(b"data"))
    output = BytesIO()
    local.download("orders/1/file.txt", output)
    assert output.getvalue() == b"data"

    class Client:
        def upload_fileobj(self, source, bucket, key, Callback=None):
            self.uploaded = (bucket, key, source.read())

        def download_fileobj(self, bucket, key, destination, Callback=None):
            destination.write(b"remote")

        def list_objects_v2(self, Bucket, MaxKeys):
            assert (Bucket, MaxKeys) == ("kms", 1)
            return {}

        def generate_presigned_url(self, operation, Params, ExpiresIn):
            return f"https://signed.example/{Params['Key']}?ttl={ExpiresIn}"

    client = Client()
    s3 = S3CompatibleProvider(client, "kms")
    s3.upload("customers/1/a.txt", BytesIO(b"a"))
    assert client.uploaded == ("kms", "customers/1/a.txt", b"a")
    assert s3.is_online() is True
    assert s3.signed_download_url("customers/1/a.txt", 120).endswith("?ttl=120")
