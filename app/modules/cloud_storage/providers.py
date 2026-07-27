"""Provider interface plus local and S3-compatible implementations."""

from pathlib import Path
from typing import BinaryIO, Protocol


class StorageProvider(Protocol):
    def upload(self, object_key: str, source: BinaryIO, progress=None) -> None: ...
    def download(self, object_key: str, destination: BinaryIO, progress=None) -> None: ...
    def is_online(self) -> bool: ...
    def signed_download_url(self, object_key: str, expires_in: int = 900) -> str: ...


class LocalStorageProvider:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, object_key: str, source: BinaryIO, progress=None) -> None:
        target = self._path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as output:
            _copy(source, output, progress)

    def download(self, object_key: str, destination: BinaryIO, progress=None) -> None:
        with self._path(object_key).open("rb") as source:
            _copy(source, destination, progress)

    def is_online(self) -> bool:
        return True

    def signed_download_url(self, object_key: str, expires_in: int = 900) -> str:
        del expires_in
        return self._path(object_key).as_uri()

    def _path(self, key: str) -> Path:
        path = (self.root / Path(key)).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("Object key escapes storage root")
        return path


class S3CompatibleProvider:
    """S3 adapter accepting any boto3-compatible client; credentials stay external."""

    def __init__(self, client, bucket: str) -> None:
        if not bucket:
            raise ValueError("Cloud bucket is required")
        self.client, self.bucket = client, bucket

    def upload(self, object_key: str, source: BinaryIO, progress=None) -> None:
        self.client.upload_fileobj(source, self.bucket, object_key, Callback=progress)

    def download(self, object_key: str, destination: BinaryIO, progress=None) -> None:
        self.client.download_fileobj(self.bucket, object_key, destination, Callback=progress)

    def is_online(self) -> bool:
        try:
            # HeadBucket can require listAllBucketNames on Backblaze even when an
            # application key is correctly restricted to this one bucket. Testing
            # a one-item listing verifies the permissions the ERP actually needs.
            self.client.list_objects_v2(Bucket=self.bucket, MaxKeys=1)
            return True
        except Exception:
            return False

    def signed_download_url(self, object_key: str, expires_in: int = 900) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=max(60, min(expires_in, 604800)),
        )

    @classmethod
    def for_backblaze(
        cls,
        *,
        endpoint_url: str,
        key_id: str,
        application_key: str,
        bucket: str,
    ) -> "S3CompatibleProvider":
        """Create a private Backblaze B2 provider through its S3-compatible API."""

        if not all((endpoint_url, key_id, application_key, bucket)):
            raise ValueError("Complete Backblaze connection details are required")
        import boto3
        from botocore.config import Config

        client = boto3.client(
            "s3",
            endpoint_url=endpoint_url.rstrip("/"),
            aws_access_key_id=key_id,
            aws_secret_access_key=application_key,
            config=Config(signature_version="s3v4"),
        )
        return cls(client, bucket)


def _copy(source: BinaryIO, destination: BinaryIO, progress=None) -> None:
    while chunk := source.read(1024 * 1024):
        destination.write(chunk)
        if progress:
            progress(len(chunk))
