"""Artwork persistence and version history."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.artwork.models import Artwork, ArtworkApproval, ArtworkVersion
from app.modules.artwork.schemas import StoredArtworkFile


class ArtworkRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def create(
        self,
        *,
        title: str,
        tags: str,
        customer_id: int | None,
        order_id: int | None,
        stored: StoredArtworkFile,
        notes: str,
    ) -> Artwork:
        with session_scope(self.factory) as session:
            artwork = Artwork(title=title, tags=tags, customer_id=customer_id, order_id=order_id)
            artwork.versions.append(self._version(1, stored, notes))
            session.add(artwork)
            session.flush()
            artwork_id = artwork.id
        result = self.get(artwork_id)
        if result is None:
            raise RuntimeError("Artwork could not be reloaded")
        return result

    def add_version(self, artwork_id: int, stored: StoredArtworkFile, notes: str) -> Artwork | None:
        with session_scope(self.factory) as session:
            artwork = session.scalar(
                select(Artwork)
                .where(Artwork.id == artwork_id)
                .options(selectinload(Artwork.versions))
            )
            if artwork is None:
                return None
            number = max((version.version_number for version in artwork.versions), default=0) + 1
            artwork.versions.append(self._version(number, stored, notes))
        return self.get(artwork_id)

    def list(self, query: str = "") -> list[Artwork]:
        from app.modules.customers.models import Customer
        from app.modules.orders.models import Order

        with session_scope(self.factory) as session:
            statement = (
                select(Artwork)
                .outerjoin(Artwork.customer)
                .outerjoin(Artwork.order)
                .options(
                    selectinload(Artwork.customer),
                    selectinload(Artwork.order),
                    selectinload(Artwork.versions).selectinload(ArtworkVersion.approvals),
                )
            )
            if query:
                pattern = f"%{query}%"
                statement = statement.where(
                    or_(
                        Artwork.title.ilike(pattern),
                        Artwork.tags.ilike(pattern),
                        Customer.name.ilike(pattern),
                        Order.order_number.ilike(pattern),
                    )
                )
            return list(session.scalars(statement.order_by(Artwork.updated_at.desc())).unique())

    def get(self, artwork_id: int) -> Artwork | None:
        with session_scope(self.factory) as session:
            return session.scalar(
                select(Artwork)
                .where(Artwork.id == artwork_id)
                .options(
                    selectinload(Artwork.customer),
                    selectinload(Artwork.order),
                    selectinload(Artwork.versions).selectinload(ArtworkVersion.approvals),
                )
            )

    def add_approval(
        self,
        version_id: int,
        status: str,
        note: str,
        user_id: int | None,
    ) -> int | None:
        with session_scope(self.factory) as session:
            version = session.get(ArtworkVersion, version_id)
            if version is None:
                return None
            session.add(
                ArtworkApproval(
                    artwork_version_id=version_id,
                    status=status,
                    note=note,
                    approved_by_user_id=user_id,
                )
            )
            return version.artwork_id

    @staticmethod
    def _version(number: int, stored: StoredArtworkFile, notes: str) -> ArtworkVersion:
        return ArtworkVersion(
            version_number=number,
            original_filename=stored.original_filename,
            original_path=stored.original_path,
            preview_path=stored.preview_path,
            mime_type=stored.mime_type,
            file_size=stored.file_size,
            width=stored.width,
            height=stored.height,
            dpi_x=stored.dpi_x,
            dpi_y=stored.dpi_y,
            has_transparency=stored.has_transparency,
            checksum_sha256=stored.checksum_sha256,
            notes=notes,
        )
