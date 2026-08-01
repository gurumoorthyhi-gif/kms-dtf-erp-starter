"""Upload/download managers, local cache, retry, and offline synchronization."""

import hashlib
import mimetypes
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
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
        original_name: str | None = None,
    ) -> CloudFile:
        source = source.resolve()
        prefix = self._validated_prefix(prefix)
        if not source.is_file():
            raise ValueError("Invalid source file or storage path")
        display_name = original_name or source.name
        if (
            Path(display_name).name != display_name
            or not display_name.strip()
            or Path(display_name).suffix.casefold() != source.suffix.casefold()
        ):
            raise ValueError("Uploaded filename must preserve the source file format")
        key = f"{prefix}{uuid4().hex}{source.suffix.casefold()}"
        cache = self.cache_root / key
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(source.read_bytes())
        digest = hashlib.sha256(cache.read_bytes()).hexdigest()
        with session_scope(self.factory) as session:
            record = CloudFile(
                object_key=PurePosixPath(key).as_posix(),
                local_path=str(cache),
                original_name=display_name,
                content_type=mimetypes.guess_type(display_name)[0] or "",
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

    def copy(
        self,
        cloud_file_id: int,
        prefix: str,
        *,
        original_name: str | None = None,
    ) -> CloudFile:
        """Copy a managed file to another virtual folder and retain its display name."""

        record = self.get(cloud_file_id)
        with TemporaryDirectory(dir=self.cache_root) as temporary:
            source = Path(temporary) / record.original_name
            cached = Path(record.local_path)
            if cached.is_file():
                source.write_bytes(cached.read_bytes())
            else:
                self.download(cloud_file_id, source)
            copied = self.queue_upload(
                source,
                prefix,
                auto_sync=False,
                original_name=original_name,
            )
        self.synchronize_async()
        return copied

    def replace(self, cloud_file_id: int, source: Path) -> CloudFile:
        """Queue new bytes for an existing managed file without changing its identity."""

        source = source.resolve()
        if not source.is_file():
            raise ValueError("Invalid source file")
        record = self.get(cloud_file_id)
        if source.suffix.casefold() != Path(record.original_name).suffix.casefold():
            raise ValueError("Replacement file must preserve the original file format")
        payload = source.read_bytes()
        cache = Path(record.local_path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix(cache.suffix + ".replace")
        temporary.write_bytes(payload)
        temporary.replace(cache)
        with session_scope(self.factory) as session:
            stored = session.get(CloudFile, cloud_file_id)
            if stored is None:
                raise LookupError(f"Cloud file {cloud_file_id} was not found")
            stored.size_bytes = len(payload)
            stored.checksum_sha256 = hashlib.sha256(payload).hexdigest()
            stored.transfer_state = "queued"
            stored.operation = "upload"
            stored.retry_count = 0
            stored.last_error = ""
        self.synchronize_async()
        return self.get(cloud_file_id)

    def delete(self, cloud_file_id: int) -> None:
        """Delete the provider object, cached file, and local metadata."""

        record = self.get(cloud_file_id)
        if record.transfer_state == "synced":
            self.provider.delete(record.object_key)
        Path(record.local_path).unlink(missing_ok=True)
        with session_scope(self.factory) as session:
            stored = session.get(CloudFile, cloud_file_id)
            if stored is not None:
                session.delete(stored)

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

    def search_similar_images(
        self,
        source: Path,
        prefix: str = "customers",
        *,
        minimum_similarity: float = 0.75,
    ) -> list[CloudFile]:
        """Return cached images ranked by private, rotation-tolerant visual similarity."""

        import cv2
        import numpy as np

        query = cv2.imread(str(source.resolve()), cv2.IMREAD_COLOR)
        if query is None:
            raise ValueError("Select a valid image file")

        feature_detector = cv2.SIFT_create(
            nfeatures=1200,
            contrastThreshold=0.018,
            edgeThreshold=14,
        )

        def perceptual_hash(image):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (17, 16), interpolation=cv2.INTER_AREA)
            return resized[:, 1:] > resized[:, :-1]

        def crops(image):
            height, width = image.shape[:2]
            results = [image]
            for scale in (0.80, 0.65, 0.50):
                crop_width, crop_height = int(width * scale), int(height * scale)
                left, top = (width - crop_width) // 2, (height - crop_height) // 2
                results.append(image[top : top + crop_height, left : left + crop_width])
            shortest = min(height, width)
            for scale in (0.95, 0.78, 0.62):
                side = max(24, int(shortest * scale))
                for vertical in (0.0, 0.25, 0.50, 0.75, 1.0):
                    top = int((height - side) * vertical)
                    for horizontal in (0.0, 0.5, 1.0):
                        left = int((width - side) * horizontal)
                        results.append(image[top : top + side, left : left + side])
            return results

        def features(image):
            resized = cv2.resize(image, (160, 160), interpolation=cv2.INTER_AREA)
            regions = crops(resized)
            histograms = []
            for region in regions:
                hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
                histogram = cv2.calcHist([hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])
                cv2.normalize(histogram, histogram)
                histograms.append(histogram)
            height, width = image.shape[:2]
            scale = max(1.0, 720.0 / max(height, width))
            enhanced = cv2.resize(
                image,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_CUBIC,
            )
            gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
            gray = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)
            blurred = cv2.GaussianBlur(gray, (0, 0), 1.1)
            gray = cv2.addWeighted(gray, 1.45, blurred, -0.45, 0)
            keypoints, descriptors = feature_detector.detectAndCompute(gray, None)
            hashes = [
                perceptual_hash(np.rot90(region, turns).copy())
                for region in regions
                for turns in range(4)
            ]
            return hashes, histograms, keypoints, descriptors

        query_hashes, query_histogram, query_keypoints, query_descriptors = features(query)
        query_digest = hashlib.sha256(source.resolve().read_bytes()).hexdigest()
        matcher = cv2.BFMatcher(cv2.NORM_L2)
        matches: list[tuple[float, CloudFile]] = []
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
        for record in self.list_prefix(prefix):
            if Path(record.original_name).suffix.casefold() not in image_suffixes:
                continue
            cached = Path(record.local_path)
            if not cached.is_file():
                continue
            candidate = cv2.imread(str(cached), cv2.IMREAD_COLOR)
            if candidate is None:
                continue
            if record.checksum_sha256 == query_digest:
                matches.append((1.0, record))
                continue
            (
                candidate_hashes,
                candidate_histogram,
                candidate_keypoints,
                candidate_descriptors,
            ) = features(candidate)
            pattern = max(
                1.0 - float(np.count_nonzero(query_hash != candidate_hash)) / 256.0
                for query_hash in query_hashes
                for candidate_hash in candidate_hashes
            )
            color = float(
                max(
                    cv2.compareHist(
                        query_region_histogram,
                        candidate_region_histogram,
                        cv2.HISTCMP_CORREL,
                    )
                    for query_region_histogram in query_histogram
                    for candidate_region_histogram in candidate_histogram
                )
            )
            feature_score = 0.0
            verified_feature_score = 0.0
            if query_descriptors is not None and candidate_descriptors is not None:
                pairs = matcher.knnMatch(query_descriptors, candidate_descriptors, k=2)
                good = [
                    first
                    for pair in pairs
                    if len(pair) == 2
                    for first, second in [pair]
                    if first.distance < 0.72 * second.distance
                ]
                feature_base = max(
                    12,
                    int(min(len(query_keypoints), len(candidate_keypoints)) * 0.30),
                )
                feature_score = min(1.0, len(good) / feature_base)
                if len(good) >= 6:
                    query_points = np.float32(
                        [query_keypoints[item.queryIdx].pt for item in good]
                    ).reshape(-1, 1, 2)
                    candidate_points = np.float32(
                        [candidate_keypoints[item.trainIdx].pt for item in good]
                    ).reshape(-1, 1, 2)
                    _transform, mask = cv2.findHomography(
                        query_points,
                        candidate_points,
                        cv2.RANSAC,
                        5.0,
                    )
                    if mask is not None:
                        inliers = int(mask.ravel().sum())
                        inlier_ratio = inliers / len(good)
                        if inliers >= 8 and inlier_ratio >= 0.55:
                            verified_feature_score = min(
                                1.0,
                                (inliers / 18.0) * 0.65 + inlier_ratio * 0.35,
                            )
            if query_descriptors is None or candidate_descriptors is None:
                similarity = (pattern * 0.72) + (max(0.0, color) * 0.28)
            else:
                similarity = (pattern * 0.43) + (max(0.0, color) * 0.20) + (feature_score * 0.37)
                if verified_feature_score > 0:
                    similarity = max(
                        similarity,
                        0.76 + (verified_feature_score * 0.22),
                    )
            global_evidence_is_strong = pattern >= 0.84 and (color >= 0.48 or feature_score >= 0.38)
            if similarity >= minimum_similarity and (
                verified_feature_score > 0 or global_evidence_is_strong
            ):
                matches.append((similarity, record))
        matches.sort(key=lambda item: item[0], reverse=True)
        return [record for _score, record in matches]

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
