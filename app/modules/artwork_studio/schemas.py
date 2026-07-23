"""Image editing and inspection records."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EditSpec:
    crop: tuple[int, int, int, int] | None = None
    resize: tuple[int, int] | None = None
    rotation_degrees: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False


@dataclass(frozen=True, slots=True)
class ImageInspection:
    width: int
    height: int
    dpi_x: int
    dpi_y: int
    has_transparency: bool
    colour_profile: str
    print_ready_300_dpi: bool


@dataclass(frozen=True, slots=True)
class StudioDocument:
    artwork_id: int
    title: str
    version_number: int
    original_path: Path
    preview_path: Path
    inspection: ImageInspection
