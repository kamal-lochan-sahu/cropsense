"""Generate CropSense brand assets (PWA icons, favicon, social preview image).

Usage:
    python scripts/make_icons.py

Needs Pillow (listed in requirements-dev.txt). Draws everything with shapes, so it does not
depend on an emoji font. Output goes to app/static/icons and app/static/img.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "app" / "static" / "icons"
IMG_DIR = ROOT / "app" / "static" / "img"

GREEN_DARK = (27, 67, 50)
GREEN = (45, 106, 79)
GREEN_MID = (82, 183, 136)
GREEN_LIGHT = (183, 228, 199)
WHITE = (255, 255, 255)
SUPERSAMPLE = 4

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path if bold else path.replace("-Bold", ""), size)
    return ImageFont.load_default()


def leaf_polygon(cx: float, cy: float, length: float, width: float, angle_deg: float):
    """Pointed leaf outline centred on (cx, cy), rotated by angle_deg."""
    steps = 80
    top, bottom = [], []
    for i in range(steps + 1):
        t = i / steps
        half = width / 2 * math.sin(math.pi * t) ** 0.85 * (1 - 0.18 * t)
        x = (t - 0.5) * length
        top.append((x, -half))
        bottom.append((x, half))
    outline = top + bottom[::-1]
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in outline]


def draw_mark(draw: ImageDraw.ImageDraw, size: int, scale: float) -> None:
    """Draw the leaf-and-stem mark centred in a size x size canvas."""
    angle = -40
    cx, cy = size * 0.53, size * 0.46
    length, width = size * scale, size * scale * 0.60
    draw.polygon(leaf_polygon(cx, cy, length, width, angle), fill=GREEN_LIGHT)

    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    tail = (cx - ux * length * 0.50, cy - uy * length * 0.50)
    tip = (cx + ux * length * 0.40, cy + uy * length * 0.40)
    draw.line([tail, tip], fill=GREEN, width=max(2, int(size * 0.022)))
    # small side veins
    for frac in (0.30, 0.52, 0.72):
        bx = tail[0] + (tip[0] - tail[0]) * frac
        by = tail[1] + (tip[1] - tail[1]) * frac
        for sign in (-1, 1):
            va = a + sign * math.radians(48)
            end = (bx + math.cos(va) * length * 0.17, by + math.sin(va) * length * 0.17)
            draw.line([(bx, by), end], fill=GREEN_MID, width=max(1, int(size * 0.012)))
    # stem
    stem_end = (tail[0] - size * 0.07, tail[1] + size * 0.11)
    draw.line([tail, stem_end], fill=GREEN_LIGHT, width=max(3, int(size * 0.034)))


def icon(size: int, *, rounded: bool, scale: float) -> Image.Image:
    big = size * SUPERSAMPLE
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if rounded:
        draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(big * 0.22), fill=GREEN)
    else:
        draw.rectangle([0, 0, big, big], fill=GREEN)
    draw_mark(draw, big, scale)
    return img.resize((size, size), Image.LANCZOS)


def social_image() -> Image.Image:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), GREEN_DARK)
    draw = ImageDraw.Draw(img)
    # soft diagonal gradient
    for y in range(h):
        mix = y / h
        colour = tuple(
            int(GREEN_DARK[i] * (1 - mix * 0.45) + GREEN[i] * mix * 0.45) for i in range(3)
        )
        draw.line([(0, y), (w, y)], fill=colour)
    draw.rectangle([0, 0, w, 10], fill=GREEN_MID)

    mark = icon(260, rounded=True, scale=0.62)
    img.paste(mark, (90, 150), mark)

    draw.text((400, 165), "CropSense", font=font(104), fill=WHITE)
    draw.text(
        (404, 295), "AI-assisted crop recommendation", font=font(40, bold=False), fill=GREEN_LIGHT
    )
    draw.text(
        (404, 360),
        "22 crops  |  21 languages  |  Free and open source",
        font=font(30, bold=False),
        fill=GREEN_MID,
    )
    draw.text((404, 470), "cropsense-39bz.onrender.com", font=font(30), fill=WHITE)
    draw.text((404, 515), "by Kamal Lochan Sahu", font=font(26, bold=False), fill=GREEN_LIGHT)
    return img


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#2d6a4f"/>
  <path d="M14 46C14 26 28 14 50 12C50 34 38 48 18 48Z" fill="#b7e4c7"/>
  <path d="M16 47C24 36 33 26 46 17" stroke="#2d6a4f" stroke-width="2.4" fill="none"
        stroke-linecap="round"/>
</svg>
"""


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    icon(192, rounded=True, scale=0.62).save(ICON_DIR / "icon-192.png", optimize=True)
    icon(512, rounded=True, scale=0.62).save(ICON_DIR / "icon-512.png", optimize=True)
    # Maskable icons get cropped by the OS: full-bleed background, mark inside the safe zone.
    icon(512, rounded=False, scale=0.48).save(ICON_DIR / "icon-maskable-512.png", optimize=True)
    icon(180, rounded=False, scale=0.56).save(ICON_DIR / "apple-touch-icon.png", optimize=True)
    icon(32, rounded=True, scale=0.66).save(ICON_DIR / "favicon-32.png", optimize=True)
    (ICON_DIR / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8")
    social_image().save(IMG_DIR / "og-image.png", optimize=True)
    print("Wrote icons to", ICON_DIR, "and social image to", IMG_DIR)


if __name__ == "__main__":
    main()
