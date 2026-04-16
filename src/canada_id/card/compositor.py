"""Composite barcodes onto card template images."""

from PIL import Image

from canada_id.card.layout import BarcodeRegion


def _scale_to_region(
    barcode: Image.Image,
    region_w: int,
    region_h: int,
) -> Image.Image:
    """Scale barcode to fit within the target region.

    Preserves aspect ratio by fitting to the smaller dimension.

    Args:
        barcode: Source barcode image.
        region_w: Target region width in pixels.
        region_h: Target region height in pixels.

    Returns:
        Scaled barcode image.
    """
    bw, bh = barcode.size
    scale = min(region_w / bw, region_h / bh)
    new_w = max(1, int(bw * scale))
    new_h = max(1, int(bh * scale))
    return barcode.resize((new_w, new_h), Image.LANCZOS)


def _stack_barcodes(
    pdf417: Image.Image,
    code39: Image.Image | None,
    gap: int = 10,
) -> Image.Image:
    """Stack Code 39 above PDF417 with a gap.

    Args:
        pdf417: PDF417 barcode image.
        code39: Optional Code 39 barcode image.
        gap: Pixel gap between the two barcodes.

    Returns:
        Combined image (Code 39 on top if present).
    """
    if code39 is None:
        return pdf417

    combined_w = max(code39.width, pdf417.width)
    combined_h = code39.height + gap + pdf417.height
    combined = Image.new("RGBA", (combined_w, combined_h), "white")

    c39_x = (combined_w - code39.width) // 2
    combined.paste(code39, (c39_x, 0))

    p417_x = (combined_w - pdf417.width) // 2
    combined.paste(pdf417, (p417_x, code39.height + gap))

    return combined


def composite_barcode_on_card(
    card_image: Image.Image,
    pdf417_image: Image.Image,
    barcode_region: BarcodeRegion,
    code39_image: Image.Image | None = None,
) -> Image.Image:
    """Overlay barcode(s) onto a card template image.

    Takes fractional BarcodeRegion coordinates instead of
    hardcoded pixel values, making it work with any card size
    or resolution.

    Args:
        card_image: Base card template (any mode).
        pdf417_image: PDF417 barcode image.
        barcode_region: Fractional placement region.
        code39_image: Optional Code 39 barcode image.

    Returns:
        New card image with barcodes composited.
    """
    card = card_image.convert("RGBA")
    card_w, card_h = card.size

    region_x = int(barcode_region.x_frac * card_w)
    region_y = int(barcode_region.y_frac * card_h)
    region_w = int(barcode_region.w_frac * card_w)
    region_h = int(barcode_region.h_frac * card_h)

    pdf417 = pdf417_image.convert("RGBA")
    code39 = None
    if code39_image is not None:
        code39 = code39_image.convert("RGBA")

    stacked = _stack_barcodes(pdf417, code39)
    scaled = _scale_to_region(stacked, region_w, region_h)

    rotation = barcode_region.rotation_deg
    if rotation != 0.0:
        scaled = scaled.rotate(
            rotation,
            expand=True,
            fillcolor=(255, 255, 255, 0),
        )

    sw, sh = scaled.size
    paste_x = region_x + (region_w - sw) // 2
    paste_y = region_y + (region_h - sh) // 2

    output = card.copy()
    output.paste(scaled, (paste_x, paste_y), mask=scaled)

    return output.convert("RGB")
