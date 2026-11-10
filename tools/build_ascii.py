from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageOps

from build_card import ART_CELL_ASPECT

ROOT = Path(__file__).resolve().parent.parent
OUT_DARK = ROOT / "assets" / "ascii-art.txt"
OUT_LIGHT = ROOT / "assets" / "ascii-art-light.txt"

LOGIN = os.environ.get("GH_LOGIN", "N0tMaggi")
AVATAR_URL = f"https://github.com/{LOGIN}.png?size=460"

COLS = 60
RAMP = " .:-=+*#%@"


def fetch_avatar() -> Image.Image:
    resp = requests.get(AVATAR_URL, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def to_gray(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    flat = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat.alpha_composite(img)
    return ImageOps.autocontrast(flat.convert("L"), cutoff=2)


def background_is_light(gray: Image.Image) -> bool:
    w, h = gray.size
    border = [gray.getpixel((x, y)) for x in range(w) for y in (0, h - 1)]
    border += [gray.getpixel((x, y)) for y in range(h) for x in (0, w - 1)]
    return sum(border) / len(border) > 127


def render(gray: Image.Image, invert: bool) -> str:
    w, h = gray.size
    rows = max(1, round(COLS * (h / w) * ART_CELL_ASPECT))
    small = gray.resize((COLS, rows), Image.Resampling.LANCZOS)
    last = len(RAMP) - 1
    lines = []
    for y in range(rows):
        line = []
        for x in range(COLS):
            v = small.getpixel((x, y)) / 255
            if invert:
                v = 1 - v
            line.append(RAMP[round(v * last)])
        lines.append("".join(line).rstrip())
    return "\n".join(lines) + "\n"


def main() -> None:
    if len(sys.argv) > 1:
        img = Image.open(sys.argv[1])
        print(f"avatar   : {sys.argv[1]}")
    else:
        img = fetch_avatar()
        print(f"avatar   : {AVATAR_URL}")

    gray = to_gray(img)
    invert = background_is_light(gray)
    art = render(gray, invert=invert)
    OUT_DARK.parent.mkdir(exist_ok=True)
    OUT_DARK.write_text(art, encoding="utf-8")
    OUT_LIGHT.write_text(art, encoding="utf-8")
    print(f"backdrop : {'light' if invert else 'dark'} -> dense glyphs on the "
          f"{'dark' if invert else 'light'} pixels")
    print(f"wrote {OUT_DARK.name} and {OUT_LIGHT.name} ({COLS} cols)")


if __name__ == "__main__":
    main()
