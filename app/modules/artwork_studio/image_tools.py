"""Non-destructive local image loading, inspection, and transformations."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from app.modules.artwork_studio.schemas import EditSpec, ImageInspection


class ImageLoader:
    def load(self, path: Path) -> Image.Image:
        with Image.open(path) as source:
            return ImageOps.exif_transpose(source).copy()


class ImageInspector:
    def inspect(self, path: Path) -> ImageInspection:
        with Image.open(path) as image:
            dpi = image.info.get("dpi", (0, 0))
            dpi_x = round(float(dpi[0])) if dpi else 0
            dpi_y = round(float(dpi[1])) if dpi else 0
            transparency = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            profile = "Embedded ICC" if image.info.get("icc_profile") else "Unspecified"
            return ImageInspection(
                image.width,
                image.height,
                dpi_x,
                dpi_y,
                transparency,
                profile,
                dpi_x >= 300 and dpi_y >= 300,
            )


class ImageTransformer:
    def __init__(self, loader: ImageLoader | None = None) -> None:
        self.loader = loader or ImageLoader()

    def render(self, source: Path, destination: Path, spec: EditSpec) -> None:
        image = self.loader.load(source)
        if spec.crop is not None:
            left, top, right, bottom = spec.crop
            if left < 0 or top < 0 or right > image.width or bottom > image.height:
                raise ValueError("Crop rectangle is outside the image")
            if right <= left or bottom <= top:
                raise ValueError("Crop rectangle must have positive size")
            image = image.crop(spec.crop)
        if spec.resize is not None:
            width, height = spec.resize
            if width < 1 or height < 1:
                raise ValueError("Resize dimensions must be positive")
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        rotation = spec.rotation_degrees % 360
        if rotation:
            image = image.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
        if spec.flip_horizontal:
            image = ImageOps.mirror(image)
        if spec.flip_vertical:
            image = ImageOps.flip(image)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "PNG", optimize=True)


class ThumbnailCache:
    def __init__(self, directory: Path, *, maximum_size: tuple[int, int] = (512, 512)) -> None:
        self.directory = directory.resolve()
        self.maximum_size = maximum_size
        self.directory.mkdir(parents=True, exist_ok=True)

    def get(self, source: Path) -> Path:
        stat = source.stat()
        cache_name = f"{source.stem}-{stat.st_size}-{stat.st_mtime_ns}.png"
        cached = self.directory / cache_name
        if cached.is_file():
            return cached
        with Image.open(source) as image:
            image.thumbnail(self.maximum_size, Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            image.save(cached, "PNG", optimize=True)
        return cached
