import hashlib
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw

from app.database import Base, create_database_engine, create_session_factory
from app.modules.artwork import (
    ArtworkInput,
    ArtworkRepository,
    ArtworkService,
    ArtworkStorage,
    PreviewService,
)
from app.modules.customers import CustomerRepository  # noqa: F401
from app.modules.gang_sheets import GangSheetInput, GangSheetRepository, GangSheetService
from app.modules.orders import OrderRepository  # noqa: F401
from app.ui.pages.gang_sheets import LayoutHistory


def context(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'gang.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    artwork = ArtworkService(
        ArtworkRepository(factory),
        ArtworkStorage(tmp_path / "artwork", PreviewService()),
    )
    service = GangSheetService(
        GangSheetRepository(factory),
        artwork,
        tmp_path / "exports",
    )
    source = tmp_path / "checker.png"
    image = Image.new("RGBA", (1200, 1200), (0, 0, 255, 255))
    draw = ImageDraw.Draw(image)
    for x in range(1, 1200, 2):
        draw.line((x, 0, x, 1199), fill=(255, 0, 0, 255))
    image.save(source, dpi=(300, 300))
    uploaded = artwork.upload(ArtworkInput("Checker", source))
    return engine, service, uploaded.summary.id, source


def test_create_place_quantity_nest_and_metre_usage(tmp_path: Path) -> None:
    engine, service, artwork_id, _ = context(tmp_path)
    sheet = service.create(
        GangSheetInput(
            "DTF run",
            Decimal("250"),
            Decimal("250"),
            Decimal("5"),
            Decimal("3"),
        )
    )

    placed = service.add_artwork(sheet.id, artwork_id, quantity=2)

    assert len(placed.items) == 2
    assert placed.items[0].x_mm == Decimal("5.00")
    assert placed.items[1].x_mm > placed.items[0].x_mm
    assert placed.metre_usage == Decimal("0.112")
    duplicated = service.duplicate(placed.items[0].id, 1)
    assert len(duplicated.items) == 3
    engine.dispose()


def test_align_distribute_rotate_resize_and_restore(tmp_path: Path) -> None:
    engine, service, artwork_id, _ = context(tmp_path)
    sheet = service.create(GangSheetInput("Layout", Decimal("400"), Decimal("300")))
    placed = service.add_artwork(sheet.id, artwork_id, quantity=3)
    ids = tuple(item.id for item in placed.items)
    aligned = service.align(sheet.id, ids, "top")
    assert len({item.y_mm for item in aligned.items}) == 1
    distributed = service.distribute(sheet.id, ids)
    assert distributed.items[1].x_mm > distributed.items[0].x_mm
    changed = service.update_item(
        distributed.items[0].id,
        width_mm=Decimal("50"),
        height_mm=Decimal("40"),
        rotation_degrees=90,
    )
    assert changed.items[0].rotation_degrees == 90
    restored = service.restore_layout(sheet.id, placed.items)
    assert len(restored.items) == 3
    engine.dispose()


def test_deterministic_export_uses_original_resolution(tmp_path: Path) -> None:
    engine, service, artwork_id, source = context(tmp_path)
    sheet = service.create(GangSheetInput("Export", Decimal("150"), Decimal("150")))
    placed = service.add_artwork(sheet.id, artwork_id)

    first = service.export(placed.id)
    first_hash = hashlib.sha256(first.read_bytes()).hexdigest()
    second = service.export(placed.id)

    assert hashlib.sha256(second.read_bytes()).hexdigest() == first_hash
    with Image.open(source) as original, Image.open(second) as exported:
        assert exported.size == (1772, 1772)
        offset = GangSheetService._mm_to_px(Decimal("5"))
        assert (
            exported.crop((offset, offset, offset + 1200, offset + 1200)).tobytes()
            == original.tobytes()
        )
    engine.dispose()


def test_layout_history_supports_undo_and_redo(tmp_path: Path) -> None:
    engine, service, artwork_id, _ = context(tmp_path)
    sheet = service.create(GangSheetInput("History", Decimal("200"), Decimal("200")))
    before = sheet.items
    after = service.add_artwork(sheet.id, artwork_id).items
    history = LayoutHistory()
    history.record(before, after)

    assert history.undo() == before
    assert history.redo() == after
    engine.dispose()
