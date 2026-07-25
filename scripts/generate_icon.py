"""Generate the Windows multi-resolution icon from the supplied KMS logo."""

from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parents[1]
source = root / "assets" / "branding" / "kms-logo.png"
target = root / "assets" / "kms_dtf_erp.ico"

logo = Image.open(source).convert("RGBA")
bounding_box = logo.getchannel("A").getbbox()
if bounding_box is None:
    raise ValueError("KMS logo contains no visible pixels")
logo = logo.crop(bounding_box)
logo.thumbnail((224, 224), Image.Resampling.LANCZOS)
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
image.alpha_composite(logo, ((256 - logo.width) // 2, (256 - logo.height) // 2))
image.save(
    target,
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
