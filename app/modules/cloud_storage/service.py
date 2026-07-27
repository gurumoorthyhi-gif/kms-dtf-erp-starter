"""Upload/download managers, local cache, retry, and offline synchronization."""

import hashlib
import mimetypes
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from threading import Lock
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
FOLDER_MARKER = ".keep"


class CloudStorageService:
    def __init__(
        self, factory: SessionFactory, provider: StorageProvider, cache_root: Path
    ) -> None:
        self.factory, self.provider = factory, provider
        self.cache_root = cache_root.resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self._upload_completed = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cloud-sync")
        self._sync_lock = Lock()
        self._sync_future: Future | None = None

    def set_provider(self, provider: StorageProvider) -> None:
        """Switch providers without discarding locally queued files."""

        self.provider = provider

    def set_upload_completed_callback(self, callback) -> None:
        self._upload_completed = callback

    def queue_upload(
        self,
        source: Path,
        prefix: str,
        *,
        auto_sync: bool = True,
    ) -> CloudFile:
        source = source.resolve()
        prefix = self._validated_prefix(prefix)
        if not source.is_file():
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
        if auto_sync and self.provider.is_online():
            self.synchronize()
        return self.get(record_id)

    def synchronize_async(self) -> Future:
        """Drain the offline queue on one background worker without duplicate jobs."""

        with self._sync_lock:
            if self._sync_future is None or self._sync_future.done():
                self._sync_future = self._executor.submit(self._drain_queue)
            return self._sync_future

    def _drain_queue(self) -> int:
        total = 0
        while True:
            completed = self.synchronize()
            total += completed
            pending = self.list_files(states=("queued", "failed"))
            retryable = [item for item in pending if item.retry_count < 3]
            if completed == 0 or not retryable:
                return total

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def ensure_folder(self, prefix: str, *, auto_sync: bool = True) -> CloudFile:
        """Create a durable virtual-folder marker, queued safely when offline."""

        prefix = self._validated_prefix(prefix)
        key = f"{prefix}{FOLDER_MARKER}"
        with session_scope(self.factory) as session:
            existing = session.scalar(select(CloudFile).where(CloudFile.object_key == key))
            if existing is not None:
                existing_id = existing.id
            else:
                cache = self.cache_root / key
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(b"")
                marker = CloudFile(
                    object_key=key,
                    local_path=str(cache),
                    original_name=FOLDER_MARKER,
                    content_type="application/x-directory",
                    size_bytes=0,
                    checksum_sha256=hashlib.sha256(b"").hexdigest(),
                    transfer_state="queued",
                    operation="folder",
                )
                session.add(marker)
                session.flush()
                existing_id = marker.id
        if auto_sync and self.provider.is_online():
            self.synchronize()
        return self.get(existing_id)

    def ensure_folders(self, prefixes) -> list[CloudFile]:
        records = [self.ensure_folder(prefix, auto_sync=False) for prefix in prefixes]
        if self.provider.is_online():
            self.synchronize()
        return records

    def ensure_folders_async(self, prefixes) -> list[CloudFile]:
        """Record virtual folders locally and upload markers in the background."""

        records = [self.ensure_folder(prefix, auto_sync=False) for prefix in prefixes]
        self.synchronize_async()
        return records

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

    def access_url(self, cloud_file_id: int, *, expires_in: int = 900) -> str:
        """Return a temporary provider URL after the caller's ERP permission check."""

        record = self.get(cloud_file_id)
        if record.transfer_state != "synced":
            raise RuntimeError("The file has not finished uploading")
        return self.provider.signed_download_url(record.object_key, expires_in)

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
                if (
                    self._upload_completed is not None
                    and record.operation != "folder"
                    and not record.google_drive_file_id
                ):
                    try:
                        drive_file_id = self._upload_completed(record)
                        if drive_file_id:
                            self._google_file(record.id, drive_file_id)
                    except Exception as error:
                        self._state(
                            record.id,
                            "synced",
                            f"Google Drive catalog pending: {error}",
                        )
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

    def list_prefix(self, prefix: str, *, include_markers: bool = False) -> list[CloudFile]:
        prefix = self._validated_prefix(prefix)
        with session_scope(self.factory) as session:
            statement = (
                select(CloudFile)
                .where(CloudFile.object_key.like(f"{prefix}%"))
                .order_by(CloudFile.created_at.desc())
            )
            if not include_markers:
                statement = statement.where(CloudFile.original_name != FOLDER_MARKER)
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

    def _google_file(self, record_id: int, drive_file_id: str) -> None:
        with session_scope(self.factory) as session:
            record = session.get(CloudFile, record_id)
            if record:
                record.google_drive_file_id = drive_file_id

    @staticmethod
    def _validated_prefix(prefix: str) -> str:
        normalized = PurePosixPath(prefix.strip("/")).as_posix()
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or ".." in path.parts
            or not any(f"{normalized}/".startswith(allowed) for allowed in ALLOWED_PREFIXES)
        ):
            raise ValueError("Invalid storage path")
        return f"{normalized}/"
