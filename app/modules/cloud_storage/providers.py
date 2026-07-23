"""Provider interface plus local and S3-compatible implementations."""

from pathlib import Path
from typing import BinaryIO, Protocol


class StorageProvider(Protocol):
    def upload(self, object_key: str, source: BinaryIO, progress=None) -> None: ...
    def download(self, object_key: str, destination: BinaryIO, progress=None) -> None: ...
    def is_online(self) -> bool: ...


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
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


def _copy(source: BinaryIO, destination: BinaryIO, progress=None) -> None:
    while chunk := source.read(1024 * 1024):
        destination.write(chunk)
        if progress:
            progress(len(chunk))
