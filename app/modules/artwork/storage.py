"""Managed artwork storage that preserves immutable originals."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from app.modules.artwork.preview import PreviewService
from app.modules.artwork.schemas import StoredArtworkFile

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


class ArtworkStorage:
    def __init__(self, root: Path, preview_service: PreviewService) -> None:
        self.root = root.resolve()
        self.preview_service = preview_service
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self, source: Path, version_number: int, *, artwork_key: str | None = None
    ) -> tuple[str, StoredArtworkFile]:
        source = source.resolve()
        if not source.is_file() or source.suffix.casefold() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Select a supported raster artwork file")
        key = artwork_key or uuid4().hex
        folder = self.root / key
        original = folder / "originals" / f"v{version_number}{source.suffix.casefold()}"
        preview = folder / "previews" / f"v{version_number}.png"
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, original)
        metadata = self.preview_service.create_thumbnail(original, preview)
        digest = hashlib.sha256()
        with original.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return key, StoredArtworkFile(
            original_filename=source.name,
            original_path=self._relative(original),
            preview_path=self._relative(preview),
            mime_type=metadata.mime_type,
            file_size=original.stat().st_size,
            width=metadata.width,
            height=metadata.height,
            dpi_x=metadata.dpi_x,
            dpi_y=metadata.dpi_y,
            has_transparency=metadata.has_transparency,
            checksum_sha256=digest.hexdigest(),
        )

    def resolve(self, managed_path: str) -> Path:
        candidate = (self.root / Path(managed_path)).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Artwork path escapes managed storage")
        return candidate

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()
