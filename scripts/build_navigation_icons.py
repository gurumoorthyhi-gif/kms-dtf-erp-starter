"""Extract transparent navigation symbols from the supplied KMS icon sheet."""

from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "assets" / "icons" / "kms-dtf-erp-icon-sheet.png"
OUTPUT = ROOT / "assets" / "icons" / "navigation"

X_POSITIONS = (47, 204, 356, 503, 652, 803, 950, 1093, 1237, 1380)
Y_POSITIONS = (174, 346, 516, 684)
TILE_SIZE = (116, 110)
SYMBOL_BOX = (14, 8, 102, 96)
OUTPUT_SIZE = (96, 96)

# name: (row, column) in the source sheet
ICON_CELLS = {
    "dashboard": (0, 0),
    "customers": (0, 1),
    "orders": (0, 3),
    "artwork": (0, 4),
    "gang_sheets": (0, 5),
    "products": (0, 6),
    "inventory": (0, 7),
    "purchases": (0, 8),
    "suppliers": (0, 9),
    "production": (1, 0),
    "packing": (1, 3),
    "dispatch": (1, 4),
    "invoices": (1, 6),
    "payments": (1, 7),
    "reports": (2, 2),
    "email": (2, 8),
    "whatsapp": (2, 9),
    "ai_tools": (3, 0),
    "cloud_storage": (3, 4),
    "backup": (3, 5),
    "settings": (3, 6),
    "users_roles": (3, 7),
    "notifications": (3, 8),
    "logout": (3, 9),
}


def main() -> None:
    sheet = Image.open(SHEET).convert("RGBA")
    if sheet.size != (1536, 1024):
        raise ValueError(f"Expected 1536x1024 icon sheet, got {sheet.size}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    width, height = TILE_SIZE
    for name, (row, column) in ICON_CELLS.items():
        left, top = X_POSITIONS[column], Y_POSITIONS[row]
        tile = sheet.crop((left, top, left + width, top + height))
        symbol = tile.crop(SYMBOL_BOX).resize(
            OUTPUT_SIZE,
            Image.Resampling.LANCZOS,
        )
        red, green, blue, _ = symbol.split()
        brightness = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        # The supplied sheet places every symbol on a near-black navy card.
        # Convert only those dark pixels to a soft alpha edge, leaving the
        # original colorful artwork untouched.
        alpha = brightness.point(lambda value: max(0, min(255, round((value - 74) * 8.5)))).filter(
            ImageFilter.GaussianBlur(0.35)
        )
        symbol.putalpha(alpha)
        symbol.save(
            OUTPUT / f"{name}.png",
            optimize=True,
        )


if __name__ == "__main__":
    main()
