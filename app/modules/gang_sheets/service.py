"""Gang sheet layout operations and deterministic original-quality export."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from PIL import Image

from app.modules.artwork import ArtworkService
from app.modules.authentication import AuthenticationService
from app.modules.gang_sheets.repository import GangSheetRepository
from app.modules.gang_sheets.schemas import GangSheetDetails, GangSheetInput, Placement

MM_PER_INCH = Decimal("25.4")
EXPORT_DPI = Decimal("300")


class GangSheetService:
    def __init__(
        self,
        repository: GangSheetRepository,
        artwork_service: ArtworkService,
        export_directory: Path,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.artwork_service = artwork_service
        self.export_directory = export_directory.resolve()
        self.export_directory.mkdir(parents=True, exist_ok=True)
        self.authentication_service = authentication_service

    def create(self, data: GangSheetInput) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        if (
            not data.name.strip()
            or data.width_mm <= 0
            or data.length_mm <= 0
            or data.margin_mm < 0
            or data.spacing_mm < 0
            or data.margin_mm * 2 >= min(data.width_mm, data.length_mm)
        ):
            raise ValueError("Gang sheet dimensions, margins, or spacing are invalid")
        return self._details(
            self.repository.create(
                GangSheetInput(
                    data.name.strip(),
                    data.width_mm,
                    data.length_mm,
                    data.margin_mm,
                    data.spacing_mm,
                    data.order_id,
                )
            )
        )

    def list(self) -> list[GangSheetDetails]:
        self._require("gang_sheets.view")
        return [self._details(sheet) for sheet in self.repository.list()]

    def get(self, sheet_id: int) -> GangSheetDetails:
        self._require("gang_sheets.view")
        sheet = self.repository.get(sheet_id)
        if sheet is None:
            raise LookupError("Gang sheet not found")
        return self._details(sheet)

    def resize_sheet(
        self,
        sheet_id: int,
        *,
        width_mm: Decimal,
        length_mm: Decimal,
        margin_mm: Decimal,
        spacing_mm: Decimal,
    ) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        if width_mm <= 0 or length_mm <= 0 or margin_mm < 0 or spacing_mm < 0:
            raise ValueError("Invalid gang sheet size")
        return self._details(
            self.repository.update_sheet(
                sheet_id,
                width_mm=width_mm,
                length_mm=length_mm,
                margin_mm=margin_mm,
                spacing_mm=spacing_mm,
            )
        )

    def add_artwork(self, sheet_id: int, artwork_id: int, *, quantity: int = 1) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        if quantity < 1 or quantity > 1000:
            raise ValueError("Quantity must be between 1 and 1000")
        artwork = self.artwork_service.get_artwork(artwork_id)
        version = artwork.summary.latest_version
        dpi_x = version.dpi_x or 300
        dpi_y = version.dpi_y or 300
        width_mm = Decimal(version.width) / Decimal(dpi_x) * MM_PER_INCH
        height_mm = Decimal(version.height) / Decimal(dpi_y) * MM_PER_INCH
        sheet = self.get(sheet_id)
        for _ in range(quantity):
            self.repository.add_item(
                sheet_id,
                artwork_version_id=version.id,
                x_mm=sheet.margin_mm,
                y_mm=sheet.margin_mm,
                width_mm=width_mm.quantize(Decimal("0.01")),
                height_mm=height_mm.quantize(Decimal("0.01")),
            )
        return self.auto_nest(sheet_id)

    def update_item(
        self,
        item_id: int,
        *,
        x_mm: Decimal | None = None,
        y_mm: Decimal | None = None,
        width_mm: Decimal | None = None,
        height_mm: Decimal | None = None,
        rotation_degrees: int | None = None,
    ) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        values = {
            key: value
            for key, value in {
                "x_mm": x_mm,
                "y_mm": y_mm,
                "width_mm": width_mm,
                "height_mm": height_mm,
                "rotation_degrees": rotation_degrees,
            }.items()
            if value is not None
        }
        if any(value <= 0 for key, value in values.items() if key in {"width_mm", "height_mm"}):
            raise ValueError("Item dimensions must be positive")
        if rotation_degrees is not None and rotation_degrees % 90:
            raise ValueError("Rotation must use 90-degree increments")
        item, sheet = self._find_item(item_id)
        proposed_x = x_mm if x_mm is not None else item.x_mm
        proposed_y = y_mm if y_mm is not None else item.y_mm
        proposed_width = width_mm if width_mm is not None else item.width_mm
        proposed_height = height_mm if height_mm is not None else item.height_mm
        proposed_rotation = (
            rotation_degrees if rotation_degrees is not None else item.rotation_degrees
        )
        effective_width, effective_height = (
            (proposed_height, proposed_width)
            if proposed_rotation % 180
            else (proposed_width, proposed_height)
        )
        if (
            proposed_x < sheet.margin_mm
            or proposed_y < sheet.margin_mm
            or proposed_x + effective_width > sheet.width_mm - sheet.margin_mm
            or proposed_y + effective_height > sheet.length_mm - sheet.margin_mm
        ):
            raise ValueError("Artwork must remain within the sheet margins")
        sheet_id = self.repository.update_item(item_id, **values)
        return self.get(sheet_id)

    def delete_item(self, item_id: int) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        return self.get(self.repository.delete_item(item_id))

    def duplicate(self, item_id: int, quantity: int) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        if quantity < 1 or quantity > 1000:
            raise ValueError("Quantity must be between 1 and 1000")
        item, sheet = self._find_item(item_id)
        for _ in range(quantity):
            self.repository.add_item(
                sheet.id,
                artwork_version_id=item.artwork_version_id,
                x_mm=item.x_mm,
                y_mm=item.y_mm,
                width_mm=item.width_mm,
                height_mm=item.height_mm,
                rotation_degrees=item.rotation_degrees,
            )
        return self.auto_nest(sheet.id)

    def align(self, sheet_id: int, item_ids: tuple[int, ...], edge: str) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        sheet = self.get(sheet_id)
        selected = [item for item in sheet.items if item.id in item_ids]
        if not selected:
            return sheet
        if edge == "left":
            target = min(item.x_mm for item in selected)
            for item in selected:
                self.repository.update_item(item.id, x_mm=target)
        elif edge == "top":
            target = min(item.y_mm for item in selected)
            for item in selected:
                self.repository.update_item(item.id, y_mm=target)
        else:
            raise ValueError("Supported alignment edges are left and top")
        return self.get(sheet_id)

    def distribute(self, sheet_id: int, item_ids: tuple[int, ...]) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        sheet = self.get(sheet_id)
        selected = sorted(
            (item for item in sheet.items if item.id in item_ids),
            key=lambda item: item.x_mm,
        )
        if len(selected) < 3:
            return sheet
        first, last = selected[0], selected[-1]
        available = last.x_mm - first.x_mm
        step = available / Decimal(len(selected) - 1)
        for index, item in enumerate(selected[1:-1], 1):
            self.repository.update_item(item.id, x_mm=first.x_mm + step * index)
        return self.get(sheet_id)

    def auto_nest(self, sheet_id: int) -> GangSheetDetails:
        """Deterministic shelf-packing interface for repeatable automatic nesting."""

        self._require("gang_sheets.manage")
        sheet = self.get(sheet_id)
        x, y = sheet.margin_mm, sheet.margin_mm
        row_height = Decimal("0")
        maximum_x = sheet.width_mm - sheet.margin_mm
        for item in sorted(sheet.items, key=lambda value: value.id):
            width, height = self._effective_size(item)
            if x + width > maximum_x and x > sheet.margin_mm:
                x = sheet.margin_mm
                y += row_height + sheet.spacing_mm
                row_height = Decimal("0")
            if y + height > sheet.length_mm - sheet.margin_mm:
                raise ValueError("Artwork does not fit within the gang sheet")
            self.repository.update_item(item.id, x_mm=x, y_mm=y)
            x += width + sheet.spacing_mm
            row_height = max(row_height, height)
        return self.get(sheet_id)

    def preview_file(self, managed_path: str) -> Path:
        return self.artwork_service.preview_file(managed_path)

    def restore_layout(self, sheet_id: int, placements: tuple[Placement, ...]) -> GangSheetDetails:
        self._require("gang_sheets.manage")
        return self._details(self.repository.replace_items(sheet_id, placements))

    def export(self, sheet_id: int) -> Path:
        self._require("gang_sheets.manage")
        sheet = self.repository.get(sheet_id)
        if sheet is None:
            raise LookupError("Gang sheet not found")
        width_px = self._mm_to_px(sheet.width_mm)
        height_px = self._mm_to_px(sheet.length_mm)
        if width_px * height_px > 400_000_000:
            raise ValueError("Gang sheet export is too large")
        canvas = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
        for item in sorted(sheet.items, key=lambda value: (value.z_index, value.id)):
            original = self.artwork_service.original_file(item.artwork_version.original_path)
            with Image.open(original) as source:
                rendered = source.convert("RGBA")
                rendered = rendered.resize(
                    (self._mm_to_px(item.width_mm), self._mm_to_px(item.height_mm)),
                    Image.Resampling.LANCZOS,
                )
                if item.rotation_degrees % 360:
                    rendered = rendered.rotate(
                        -item.rotation_degrees,
                        expand=True,
                        resample=Image.Resampling.BICUBIC,
                    )
                canvas.alpha_composite(
                    rendered,
                    (self._mm_to_px(item.x_mm), self._mm_to_px(item.y_mm)),
                )
                rendered.close()
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", sheet.name).strip("-") or "gang-sheet"
        output = self.export_directory / f"{safe_name}-{sheet.id}.png"
        canvas.save(output, "PNG", dpi=(300, 300), compress_level=9)
        canvas.close()
        return output

    def _require(self, permission: str) -> None:
        if self.authentication_service is not None:
            self.authentication_service.require_permission(permission)

    def _find_item(self, item_id: int):
        for sheet in self.repository.list():
            loaded = self.repository.get(sheet.id)
            if loaded is not None:
                for item in loaded.items:
                    if item.id == item_id:
                        return item, loaded
        raise LookupError("Gang sheet item not found")

    @classmethod
    def _details(cls, sheet) -> GangSheetDetails:
        items = tuple(
            Placement(
                item.id,
                item.artwork_version_id,
                item.artwork_version.artwork.title,
                item.artwork_version.preview_path,
                item.x_mm,
                item.y_mm,
                item.width_mm,
                item.height_mm,
                item.rotation_degrees,
                item.z_index,
            )
            for item in sheet.items
        )
        used_length = max(
            (item.y_mm + cls._effective_size(item)[1] + sheet.margin_mm for item in items),
            default=Decimal("0"),
        )
        return GangSheetDetails(
            sheet.id,
            sheet.name,
            sheet.width_mm,
            sheet.length_mm,
            sheet.margin_mm,
            sheet.spacing_mm,
            (used_length / Decimal("1000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
            items,
        )

    @staticmethod
    def _effective_size(item) -> tuple[Decimal, Decimal]:
        if item.rotation_degrees % 180:
            return item.height_mm, item.width_mm
        return item.width_mm, item.height_mm

    @staticmethod
    def _mm_to_px(value: Decimal) -> int:
        return max(
            1,
            int((value / MM_PER_INCH * EXPORT_DPI).to_integral_value(rounding=ROUND_HALF_UP)),
        )
