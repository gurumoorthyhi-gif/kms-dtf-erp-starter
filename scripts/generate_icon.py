"""Generate the Windows multi-resolution icon from release brand colours."""

from pathlib import Path

from PIL import Image, ImageDraw

target = Path(__file__).resolve().parents[1] / "assets" / "kms_dtf_erp.ico"
image = Image.new("RGBA", (256, 256))
pixels = image.load()
for y in range(256):
    for x in range(256):
        ratio = (x + y) / 510
        pixels[x, y] = (
            int(124 * (1 - ratio) + 6 * ratio),
            int(58 * (1 - ratio) + 182 * ratio),
            int(237 * (1 - ratio) + 212 * ratio),
            255,
        )
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((10, 10, 246, 246), radius=56, outline="white", width=5)
draw.text((73, 65), "K", fill="white", stroke_width=2, stroke_fill="white")
image.save(target, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
