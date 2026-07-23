"""Gang sheet persistence."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.gang_sheets.models import GangSheet, GangSheetItem
from app.modules.gang_sheets.schemas import GangSheetInput


class GangSheetRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def create(self, data: GangSheetInput) -> GangSheet:
        with session_scope(self.factory) as session:
            sheet = GangSheet(
                name=data.name,
                order_id=data.order_id,
                width_mm=data.width_mm,
                length_mm=data.length_mm,
                margin_mm=data.margin_mm,
                spacing_mm=data.spacing_mm,
            )
            session.add(sheet)
            session.flush()
            sheet_id = sheet.id
        return self._required(sheet_id)

    def list(self) -> list[GangSheet]:
        from app.modules.artwork.models import ArtworkVersion

        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    select(GangSheet)
                    .options(
                        selectinload(GangSheet.items)
                        .selectinload(GangSheetItem.artwork_version)
                        .selectinload(ArtworkVersion.artwork)
                    )
                    .order_by(GangSheet.updated_at.desc())
                )
            )

    def get(self, sheet_id: int) -> GangSheet | None:
        from app.modules.artwork.models import ArtworkVersion

        with session_scope(self.factory) as session:
            return session.scalar(
                select(GangSheet)
                .where(GangSheet.id == sheet_id)
                .options(
                    selectinload(GangSheet.items)
                    .selectinload(GangSheetItem.artwork_version)
                    .selectinload(ArtworkVersion.artwork)
                )
            )

    def update_sheet(self, sheet_id: int, **values) -> GangSheet:
        with session_scope(self.factory) as session:
            sheet = session.get(GangSheet, sheet_id)
            if sheet is None:
                raise LookupError("Gang sheet not found")
            for key, value in values.items():
                setattr(sheet, key, value)
        return self._required(sheet_id)

    def add_item(
        self,
        sheet_id: int,
        *,
        artwork_version_id: int,
        x_mm: Decimal,
        y_mm: Decimal,
        width_mm: Decimal,
        height_mm: Decimal,
        rotation_degrees: int = 0,
    ) -> GangSheet:
        with session_scope(self.factory) as session:
            sheet = session.get(GangSheet, sheet_id)
            if sheet is None:
                raise LookupError("Gang sheet not found")
            z_index = session.scalar(
                select(GangSheetItem.z_index)
                .where(GangSheetItem.gang_sheet_id == sheet_id)
                .order_by(GangSheetItem.z_index.desc())
                .limit(1)
            )
            session.add(
                GangSheetItem(
                    gang_sheet_id=sheet_id,
                    artwork_version_id=artwork_version_id,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    width_mm=width_mm,
                    height_mm=height_mm,
                    rotation_degrees=rotation_degrees,
                    z_index=(z_index or 0) + 1,
                )
            )
        return self._required(sheet_id)

    def update_item(self, item_id: int, **values) -> int:
        with session_scope(self.factory) as session:
            item = session.get(GangSheetItem, item_id)
            if item is None:
                raise LookupError("Gang sheet item not found")
            for key, value in values.items():
                setattr(item, key, value)
            return item.gang_sheet_id

    def delete_item(self, item_id: int) -> int:
        with session_scope(self.factory) as session:
            item = session.get(GangSheetItem, item_id)
            if item is None:
                raise LookupError("Gang sheet item not found")
            sheet_id = item.gang_sheet_id
            session.delete(item)
            return sheet_id

    def replace_items(self, sheet_id: int, placements) -> GangSheet:
        with session_scope(self.factory) as session:
            sheet = session.scalar(
                select(GangSheet)
                .where(GangSheet.id == sheet_id)
                .options(selectinload(GangSheet.items))
            )
            if sheet is None:
                raise LookupError("Gang sheet not found")
            sheet.items.clear()
            for index, placement in enumerate(placements, 1):
                sheet.items.append(
                    GangSheetItem(
                        artwork_version_id=placement.artwork_version_id,
                        x_mm=placement.x_mm,
                        y_mm=placement.y_mm,
                        width_mm=placement.width_mm,
                        height_mm=placement.height_mm,
                        rotation_degrees=placement.rotation_degrees,
                        z_index=index,
                    )
                )
        return self._required(sheet_id)

    def _required(self, sheet_id: int) -> GangSheet:
        sheet = self.get(sheet_id)
        if sheet is None:
            raise LookupError("Gang sheet not found")
        return sheet
