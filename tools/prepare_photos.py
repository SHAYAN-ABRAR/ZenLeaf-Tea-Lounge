#!/usr/bin/env python3
"""Turn source images into the menu photos the site serves.

Each image is cropped to 4:3 around its centre and saved as two WebP files in
lounge/static/lounge/img/menu/photos/: <key>-960.webp and <key>-480.webp.

    pip install pillow        # only this script needs it
    python tools/prepare_photos.py cup-green=~/Downloads/01-sencha.png plate-bun=~/Downloads/20-cardamom-bun.png

Each key must be one of the picture keys in lounge/illustrations.py. After adding a photo, give it
alt text in PHOTOS in the same file; until then the site keeps showing the drawing.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lounge.illustrations import ILLUSTRATIONS, PHOTO_WIDTHS  # noqa: E402  (plain module, no Django setup needed)

OUT = ROOT / "lounge" / "static" / "lounge" / "img" / "menu" / "photos"
RATIO = 4 / 3
QUALITY = 80


def crop_to_ratio(image):
    """The largest 4:3 area in the middle of the image."""
    width, height = image.size
    if width / height > RATIO:
        new_width = round(height * RATIO)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = round(width / RATIO)
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def main(pairs):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("This script needs Pillow: pip install pillow")
    if not pairs:
        sys.exit(__doc__)
    OUT.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        key, _, source = pair.partition("=")
        if key not in ILLUSTRATIONS or not source:
            sys.exit(f"{pair!r}: use key=path, with a key from lounge/illustrations.py")
        with Image.open(Path(source).expanduser()) as original:
            image = crop_to_ratio(original.convert("RGB"))
        for width in PHOTO_WIDTHS:
            size = (width, round(width / RATIO))
            path = OUT / f"{key}-{width}.webp"
            image.resize(size, Image.LANCZOS).save(path, "WEBP", quality=QUALITY, method=6)
            print(f"{path.relative_to(ROOT)}  {size[0]}x{size[1]}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1:])
