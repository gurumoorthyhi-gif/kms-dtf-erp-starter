"""Artwork library use cases."""

from pathlib import Path, PurePosixPath

from app.modules.artwork.repository import ArtworkRepository
from app.modules.artwork.schemas import (
    ArtworkDetails,
    ArtworkInput,
    ArtworkSummary,
    ArtworkVersionDetails,
)
from app.modules.artwork.storage import ArtworkStorage
from app.modules.authentication import AuthenticationService

APPROVAL_STATUSES = ("Pending", "Approved", "Changes Requested", "Rejected")


class ArtworkService:
    def __init__(
        self,
        repository: ArtworkRepository,
        storage: ArtworkStorage,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.authentication_service = authentication_service

    def upload(self, data: ArtworkInput) -> ArtworkDetails:
        self._require("artwork.manage")
        title = data.title.strip()
        if not title:
            raise ValueError("Artwork title is required")
        tags = self._normalize_tags(data.tags)
        _, stored = self.storage.store(data.source_path, 1)
        artwork = self.repository.create(
            title=title,
            tags=",".join(tags),
            customer_id=data.customer_id,
            order_id=data.order_id,
            stored=stored,
            notes=data.notes.strip(),
        )
        return self._details(artwork)

    def add_version(self, artwork_id: int, source_path: Path, notes: str = "") -> ArtworkDetails:
        self._require("artwork.manage")
        existing = self.repository.get(artwork_id)
        if existing is None:
            raise LookupError(f"Artwork not found: {artwork_id}")
        latest = existing.versions[-1]
        key = PurePosixPath(latest.original_path).parts[0]
        _, stored = self.storage.store(
            source_path,
            latest.version_number + 1,
            artwork_key=key,
        )
        artwork = self.repository.add_version(artwork_id, stored, notes.strip())
        if artwork is None:
            raise LookupError(f"Artwork not found: {artwork_id}")
        return self._details(artwork)

    def list_artwork(self, query: str = "") -> list[ArtworkSummary]:
        self._require("artwork.view")
        return [self._summary(artwork) for artwork in self.repository.list(query.strip())]

    def get_artwork(self, artwork_id: int) -> ArtworkDetails:
        self._require("artwork.view")
        artwork = self.repository.get(artwork_id)
        if artwork is None:
            raise LookupError(f"Artwork not found: {artwork_id}")
        return self._details(artwork)

    def record_approval(self, version_id: int, status: str, note: str = "") -> ArtworkDetails:
        self._require("artwork.approve")
        if status not in APPROVAL_STATUSES:
            raise ValueError("Invalid artwork approval status")
        artwork_id = self.repository.add_approval(
            version_id,
            status,
            note.strip(),
            self._user_id(),
        )
        if artwork_id is None:
            raise LookupError(f"Artwork version not found: {version_id}")
        return self.get_artwork(artwork_id)

    def preview_file(self, managed_path: str) -> Path:
        self._require("artwork.view")
        path = self.storage.resolve(managed_path)
        if not path.is_file():
            raise FileNotFoundError("Artwork preview is missing")
        return path

    def original_file(self, managed_path: str) -> Path:
        """Resolve an original only through managed artwork storage."""

        self._require("artwork.view")
        path = self.storage.resolve(managed_path)
        if not path.is_file():
            raise FileNotFoundError("Artwork original is missing")
        return path

    def _require(self, permission: str) -> None:
        if self.authentication_service is not None:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if self.authentication_service is None:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None

    @staticmethod
    def _normalize_tags(tags: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(tag.strip().casefold() for tag in tags if tag.strip()))

    @classmethod
    def _summary(cls, artwork) -> ArtworkSummary:
        latest = artwork.versions[-1]
        return ArtworkSummary(
            id=artwork.id,
            title=artwork.title,
            tags=tuple(filter(None, artwork.tags.split(","))),
            customer_name=artwork.customer.name if artwork.customer else "",
            order_number=artwork.order.order_number if artwork.order else "",
            version_count=len(artwork.versions),
            latest_version=cls._version(latest),
        )

    @classmethod
    def _details(cls, artwork) -> ArtworkDetails:
        return ArtworkDetails(
            summary=cls._summary(artwork),
            versions=tuple(cls._version(version) for version in artwork.versions),
        )

    @staticmethod
    def _version(version) -> ArtworkVersionDetails:
        return ArtworkVersionDetails(
            id=version.id,
            version_number=version.version_number,
            original_filename=version.original_filename,
            original_path=version.original_path,
            preview_path=version.preview_path,
            file_size=version.file_size,
            width=version.width,
            height=version.height,
            dpi_x=version.dpi_x,
            dpi_y=version.dpi_y,
            has_transparency=version.has_transparency,
            notes=version.notes,
            approval_status=version.approvals[-1].status if version.approvals else "Pending",
            created_at=version.created_at,
        )
