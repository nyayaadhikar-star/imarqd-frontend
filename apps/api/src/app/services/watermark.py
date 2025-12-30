from __future__ import annotations

import re
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def _parse_hex_color(color: str) -> Tuple[int, int, int]:
    text = color.strip().lower()
    if text.startswith("#"):
        text = text[1:]
    if re.fullmatch(r"[0-9a-f]{6}", text):
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
        return r, g, b
    # default white
    return 255, 255, 255


def _load_font(preferred_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        # Common Windows font; may fail on non-Windows
        return ImageFont.truetype("arial.ttf", preferred_size)
    except Exception:
        try:
            # PIL bundled DejaVu if available
            return ImageFont.truetype("DejaVuSans.ttf", preferred_size)
        except Exception:
            return ImageFont.load_default()


def apply_text_watermark(
    image: Image.Image,
    text: str,
    position: str = "center",
    opacity: float = 0.3,
    scale: float = 0.2,
    margin: int = 16,
    color: str = "#ffffff",
) -> Image.Image:
    if not text:
        return image

    width, height = image.size
    # Choose font size as a fraction of image width
    font_size = max(10, int(width * max(0.05, min(scale, 1.0))))
    font = _load_font(font_size)

    # Convert to RGBA for compositing
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Measure text
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except Exception:
        text_w, text_h = draw.textsize(text, font=font)

    # Compute position
    pos = position.lower().replace(" ", "-")
    x, y = 0, 0
    if pos in ("top-left", "topleft"):
        x, y = margin, margin
    elif pos in ("top-right", "topright"):
        x = width - text_w - margin
        y = margin
    elif pos in ("bottom-left", "bottomleft"):
        x = margin
        y = height - text_h - margin
    elif pos in ("bottom-right", "bottomright"):
        x = width - text_w - margin
        y = height - text_h - margin
    else:  # center
        x = (width - text_w) // 2
        y = (height - text_h) // 2

    r, g, b = _parse_hex_color(color)
    a = int(max(0.0, min(opacity, 1.0)) * 255)
    draw.text((x, y), text, font=font, fill=(r, g, b, a))

    out = Image.alpha_composite(base, overlay)
    return out.convert(image.mode)


