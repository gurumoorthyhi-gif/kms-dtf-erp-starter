"""Optimized artwork preview and image metadata generation."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.modules.artwork.schemas import ImageMetadata


class PreviewService:
    def inspect(self, source: Path) -> ImageMetadata:
        with Image.open(source) as image:
            dpi = image.info.get("dpi", (0, 0))
            has_transparency = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            return ImageMetadata(
                width=image.width,
                height=image.height,
                dpi_x=round(float(dpi[0])) if dpi else 0,
                dpi_y=round(float(dpi[1])) if dpi else 0,
                has_transparency=has_transparency,
                mime_type=Image.MIME.get(image.format or "", "application/octet-stream"),
            )

    def create_thumbnail(
        self, source: Path, destination: Path, *, maximum_size: tuple[int, int] = (640, 640)
    ) -> ImageMetadata:
        destination.parent.mkdir(parents=True, exist_ok=True)
        metadata = self.inspect(source)
        with Image.open(source) as image:
            image.thumbnail(maximum_size, Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if metadata.has_transparency else "RGB")
            image.save(destination, "PNG", optimize=True)
        return metadata
