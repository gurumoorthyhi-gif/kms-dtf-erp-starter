"""Artwork studio orchestration with new-version persistence."""

from pathlib import Path

from app.modules.artwork import ArtworkDetails, ArtworkService
from app.modules.artwork_studio.image_tools import (
    ImageInspector,
    ImageTransformer,
    ThumbnailCache,
)
from app.modules.artwork_studio.schemas import EditSpec, StudioDocument


class ArtworkStudioService:
    def __init__(
        self,
        artwork_service: ArtworkService,
        transformer: ImageTransformer,
        inspector: ImageInspector,
        thumbnail_cache: ThumbnailCache,
    ) -> None:
        self.artwork_service = artwork_service
        self.transformer = transformer
        self.inspector = inspector
        self.thumbnail_cache = thumbnail_cache

    def open_artwork(self, artwork_id: int) -> StudioDocument:
        details = self.artwork_service.get_artwork(artwork_id)
        latest = details.summary.latest_version
        original = self.artwork_service.original_file(latest.original_path)
        preview = self.thumbnail_cache.get(original)
        return StudioDocument(
            artwork_id=artwork_id,
            title=details.summary.title,
            version_number=latest.version_number,
            original_path=original,
            preview_path=preview,
            inspection=self.inspector.inspect(original),
        )

    def render_edit(self, source: Path, destination: Path, spec: EditSpec) -> None:
        self.transformer.render(source, destination, spec)

    def save_as_new_version(
        self, artwork_id: int, rendered_path: Path, notes: str
    ) -> ArtworkDetails:
        return self.artwork_service.add_version(artwork_id, rendered_path, notes)

    def edit_and_save(
        self,
        artwork_id: int,
        destination: Path,
        spec: EditSpec,
        notes: str = "Edited in Artwork Studio",
    ) -> ArtworkDetails:
        document = self.open_artwork(artwork_id)
        self.render_edit(document.original_path, destination, spec)
        return self.save_as_new_version(artwork_id, destination, notes)
