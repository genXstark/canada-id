"""Render MRZ text as a scannable image using OCR-B font simulation."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


OCR_B_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
)

DEFAULT_CHAR_WIDTH = 12
DEFAULT_CHAR_HEIGHT = 18
DEFAULT_LINE_SPACING = 4
DEFAULT_MARGIN = 20


def render_mrz_image(
    mrz_string: str,
    scale: int = 3,
    bg_color: int = 255,
    fg_color: int = 0,
) -> Image.Image:
    """Render MRZ text as a scannable monochrome image.

    Uses a monospace font rendering that mimics OCR-B for
    machine readability. Each character occupies a fixed cell.

    Args:
        mrz_string: Multi-line MRZ string.
        scale: Scale factor for higher resolution.
        bg_color: Background color (0-255). Default white.
        fg_color: Foreground/text color (0-255). Default black.

    Returns:
        PIL Image in grayscale mode suitable for OCR scanning.
    """
    lines = mrz_string.strip().split("\n")
    num_lines = len(lines)
    max_chars = max(len(line) for line in lines)

    char_w = DEFAULT_CHAR_WIDTH * scale
    char_h = DEFAULT_CHAR_HEIGHT * scale
    line_gap = DEFAULT_LINE_SPACING * scale
    margin = DEFAULT_MARGIN * scale

    img_w = (max_chars * char_w) + (2 * margin)
    img_h = (num_lines * char_h) + ((num_lines - 1) * line_gap) + (2 * margin)

    img = Image.new("L", (img_w, img_h), color=bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("cour.ttf", char_h)
    except OSError:
        try:
            font = ImageFont.truetype("Courier New", char_h)
        except OSError:
            font = ImageFont.load_default()

    for line_idx, line in enumerate(lines):
        y = margin + line_idx * (char_h + line_gap)
        for char_idx, char in enumerate(line):
            x = margin + char_idx * char_w
            draw.text((x, y), char, fill=fg_color, font=font)

    return img


def render_mrz_with_frame(
    mrz_string: str,
    scale: int = 3,
) -> Image.Image:
    """Render MRZ with a surrounding frame for visual reference.

    Adds a thin border and corner marks around the MRZ zone,
    matching the typical appearance on physical ID documents.

    Args:
        mrz_string: Multi-line MRZ string.
        scale: Scale factor.

    Returns:
        PIL Image with framed MRZ zone.
    """
    mrz_img = render_mrz_image(mrz_string, scale=scale)
    frame_margin = 8 * scale

    framed_w = mrz_img.width + 2 * frame_margin
    framed_h = mrz_img.height + 2 * frame_margin

    framed = Image.new("L", (framed_w, framed_h), color=255)
    framed.paste(mrz_img, (frame_margin, frame_margin))

    draw = ImageDraw.Draw(framed)
    border = 2 * scale
    draw.rectangle(
        [frame_margin - border, frame_margin - border,
         framed_w - frame_margin + border, framed_h - frame_margin + border],
        outline=0, width=border,
    )

    corner_len = 15 * scale
    corners = [
        (0, 0, corner_len, 0), (0, 0, 0, corner_len),
        (framed_w - corner_len, 0, framed_w, 0),
        (framed_w, 0, framed_w, corner_len),
        (0, framed_h, corner_len, framed_h),
        (0, framed_h - corner_len, 0, framed_h),
        (framed_w - corner_len, framed_h, framed_w, framed_h),
        (framed_w, framed_h - corner_len, framed_w, framed_h),
    ]
    for x1, y1, x2, y2 in corners:
        draw.line([(x1, y1), (x2, y2)], fill=0, width=border)

    return framed
