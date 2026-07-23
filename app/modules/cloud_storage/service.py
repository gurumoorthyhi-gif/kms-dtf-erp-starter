"""Upload/download managers, local cache, retry, and offline synchronization."""

import hashlib
import mimetypes
from pathlib import Path, PurePosixPath
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionFactory, session_scope
from app.modules.cloud_storage.models import CloudFile
from app.modules.cloud_storage.providers import StorageProvider

ALLOWED_PREFIXES = (
    "customers/",
    "orders/",
    "artwork/original/",
    "artwork/previews/",
    "artwork/processed/",
    "gang-sheets/",
    "invoices/",
    "dispatch/",
)


class CloudStorageService:
    def __init__(
        self, factory: SessionFactory, provider: StorageProvider, cache_root: Path
    ) -> None:
        self.factory, self.provider = factory, provider
        self.cache_root = cache_root.resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def queue_upload(self, source: Path, prefix: str) -> CloudFile:
        source = source.resolve()
        prefix = prefix.strip("/") + "/"
        if not source.is_file() or prefix not in ALLOWED_PREFIXES:
            raise ValueError("Invalid source file or storage path")
        key = f"{prefix}{uuid4().hex}{source.suffix.casefold()}"
        cache = self.cache_root / key
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(source.read_bytes())
        digest = hashlib.sha256(cache.read_bytes()).hexdigest()
        with session_scope(self.factory) as session:
            record = CloudFile(
                object_key=PurePosixPath(key).as_posix(),
                local_path=str(cache),
                original_name=source.name,
                content_type=mimetypes.guess_type(source.name)[0] or "",
                size_bytes=cache.stat().st_size,
                checksum_sha256=digest,
                transfer_state="queued",
            )
            session.add(record)
            session.flush()
            record_id = record.id
        if self.provider.is_online():
            self.synchronize()
        return self.get(record_id)

    def download(self, cloud_file_id: int, destination: Path, progress=None) -> Path:
        record = self.get(cloud_file_id)
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            with temporary.open("wb") as output:
                self.provider.download(record.object_key, output, progress)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return destination

    def synchronize(self, progress=None, max_retries: int = 3) -> int:
        if not self.provider.is_online():
            return 0
        completed = 0
        for record in self.list_files(states=("queued", "failed")):
            if record.retry_count >= max_retries:
                continue
            try:
                with Path(record.local_path).open("rb") as source:
                    self.provider.upload(record.object_key, source, progress)
                self._state(record.id, "synced", "")
                completed += 1
            except Exception as error:
                self._state(record.id, "failed", str(error), increment=True)
        return completed

    def list_files(self, states: tuple[str, ...] | None = None) -> list[CloudFile]:
        with session_scope(self.factory) as session:
            statement = select(CloudFile).order_by(CloudFile.created_at.desc())
            if states:
                statement = statement.where(CloudFile.transfer_state.in_(states))
            return list(session.scalars(statement))

    def get(self, record_id: int) -> CloudFile:
        with session_scope(self.factory) as session:
            record = session.get(CloudFile, record_id)
            if not record:
                raise LookupError("Cloud file not found")
            return record

    def _state(self, record_id: int, state: str, error: str, *, increment: bool = False) -> None:
        with session_scope(self.factory) as session:
            record = session.get(CloudFile, record_id)
            if not record:
                raise LookupError("Cloud file not found")
            record.transfer_state = state
            record.last_error = error
            if increment:
                record.retry_count += 1
