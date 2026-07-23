from pathlib import Path

from PIL import Image

from app.database import Base, create_database_engine, create_session_factory
from app.modules.artwork import (
    ArtworkInput,
    ArtworkRepository,
    ArtworkService,
    ArtworkStorage,
    PreviewService,
)
from app.modules.artwork_studio import (
    ArtworkStudioService,
    EditSpec,
    ImageInspector,
    ImageTransformer,
    ThumbnailCache,
)
from app.modules.customers import CustomerRepository  # noqa: F401
from app.modules.orders import OrderRepository  # noqa: F401


def make_source(path: Path, size: tuple[int, int] = (100, 60)) -> bytes:
    image = Image.new("RGBA", size, (120, 20, 220, 100))
    image.save(path, dpi=(300, 300), icc_profile=b"test-profile")
    return path.read_bytes()


def test_crop_resize_rotate_and_flip_are_non_destructive(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    rendered = tmp_path / "rendered.png"
    original = make_source(source)
    transformer = ImageTransformer()

    transformer.render(
        source,
        rendered,
        EditSpec(
            crop=(10, 5, 90, 55),
            resize=(40, 20),
            rotation_degrees=90,
            flip_horizontal=True,
            flip_vertical=True,
        ),
    )

    assert source.read_bytes() == original
    with Image.open(rendered) as result:
        assert result.size == (20, 40)
        assert result.mode == "RGBA"


def test_inspection_and_thumbnail_cache(tmp_path: Path) -> None:
    source = tmp_path / "large.png"
    make_source(source, (1200, 800))
    inspector = ImageInspector()
    cache = ThumbnailCache(tmp_path / "cache")

    inspection = inspector.inspect(source)
    first = cache.get(source)
    second = cache.get(source)

    assert inspection.has_transparency is True
    assert inspection.colour_profile == "Embedded ICC"
    assert inspection.print_ready_300_dpi is True
    assert first == second
    with Image.open(first) as thumbnail:
        assert thumbnail.width <= 512 and thumbnail.height <= 512


def test_studio_edit_saves_new_artwork_version(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'studio.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    artwork = ArtworkService(
        ArtworkRepository(factory),
        ArtworkStorage(tmp_path / "artwork", PreviewService()),
    )
    studio = ArtworkStudioService(
        artwork,
        ImageTransformer(),
        ImageInspector(),
        ThumbnailCache(tmp_path / "cache"),
    )
    source = tmp_path / "source.png"
    original_bytes = make_source(source)
    created = artwork.upload(ArtworkInput("Studio test", source))
    original_managed = artwork.original_file(created.summary.latest_version.original_path)
    result = tmp_path / "studio-result.png"

    updated = studio.edit_and_save(
        created.summary.id,
        result,
        EditSpec(crop=(0, 0, 80, 50), rotation_degrees=90),
    )

    assert len(updated.versions) == 2
    assert updated.summary.latest_version.width == 50
    assert updated.summary.latest_version.height == 80
    assert original_managed.read_bytes() == original_bytes
    engine.dispose()
