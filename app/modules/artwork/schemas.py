"""Artwork inputs, metadata, and presentation records."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    width: int
    height: int
    dpi_x: int
    dpi_y: int
    has_transparency: bool
    mime_type: str


@dataclass(frozen=True, slots=True)
class ArtworkInput:
    title: str
    source_path: Path
    tags: tuple[str, ...] = ()
    customer_id: int | None = None
    order_id: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ArtworkVersionDetails:
    id: int
    version_number: int
    original_filename: str
    original_path: str
    preview_path: str
    file_size: int
    width: int
    height: int
    dpi_x: int
    dpi_y: int
    has_transparency: bool
    notes: str
    approval_status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ArtworkSummary:
    id: int
    title: str
    tags: tuple[str, ...]
    customer_name: str
    order_number: str
    version_count: int
    latest_version: ArtworkVersionDetails


@dataclass(frozen=True, slots=True)
class ArtworkDetails:
    summary: ArtworkSummary
    versions: tuple[ArtworkVersionDetails, ...]


@dataclass(frozen=True, slots=True)
class StoredArtworkFile:
    original_filename: str
    original_path: str
    preview_path: str
    mime_type: str
    file_size: int
    width: int
    height: int
    dpi_x: int
    dpi_y: int
    has_transparency: bool
    checksum_sha256: str
