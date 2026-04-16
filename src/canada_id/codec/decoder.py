"""Public API for PDF417 barcode decoding.

Multi-strategy approach: tries full image first, then
progressive crops and contrast enhancement to handle
phone photos of driver's licenses.
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from canada_id.codec._pdf417dec.Decoder import PDF417Decoder


def _ensure_rgb(image: Image.Image) -> Image.Image:
    """Convert image to RGB if needed (decoder requires it)."""
    if image.mode not in ("RGB", "L"):
        return image.convert("RGB")
    return image


def _try_decode(image: Image.Image) -> list[bytes]:
    """Single decode attempt on a prepared image."""
    try:
        decoder = PDF417Decoder(image)
        count = decoder.decode()
        if count > 0:
            return [
                bytes(info.barcode_data)
                for info in decoder.barcodes_info
            ]
    except Exception:
        pass
    return []


def _enhanced_variants(image: Image.Image) -> list[Image.Image]:
    """Generate enhanced image variants for barcode detection."""
    variants = []
    img = _ensure_rgb(image)

    # Sharpen
    sharp = ImageEnhance.Sharpness(img).enhance(2.0)
    variants.append(sharp)

    # High contrast
    contrast = ImageEnhance.Contrast(img).enhance(2.0)
    variants.append(contrast)

    # Grayscale + adaptive threshold via OpenCV
    gray = np.array(img.convert("L"))
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, 8,
    )
    variants.append(Image.fromarray(adaptive))

    # Upscale small images (barcode needs enough pixels)
    w, h = img.size
    if max(w, h) < 1200:
        scale = 1200 / max(w, h)
        big = img.resize(
            (int(w * scale), int(h * scale)),
            Image.LANCZOS,
        )
        variants.append(big)

    return variants


def decode_pdf417(image: Image.Image) -> list[bytes]:
    """Decode PDF417 barcode(s) from a PIL Image.

    Uses multi-strategy approach:
    1. Try full image as-is
    2. Try bottom 50% crop (barcode on back of card)
    3. Try bottom 35% crop (tighter barcode isolation)
    4. Try enhanced variants of each crop
    5. Try upscaled versions for small images

    Args:
        image: PIL Image containing one or more PDF417 barcodes.

    Returns:
        List of decoded byte payloads, one per barcode found.
    """
    image = _ensure_rgb(image)
    w, h = image.size

    # Strategy 1: full image as-is
    result = _try_decode(image)
    if result:
        return result

    # Crop regions to try: bottom 50%, bottom 35%, bottom 25%
    crops = [
        image.crop((0, int(h * 0.50), w, h)),
        image.crop((0, int(h * 0.65), w, h)),
        image.crop((0, int(h * 0.75), w, h)),
    ]

    # Strategy 2: try each crop
    for crop in crops:
        result = _try_decode(crop)
        if result:
            return result

    # Strategy 3: enhanced variants of full image
    for variant in _enhanced_variants(image):
        result = _try_decode(variant)
        if result:
            return result

    # Strategy 4: enhanced variants of crops
    for crop in crops:
        for variant in _enhanced_variants(crop):
            result = _try_decode(variant)
            if result:
                return result

    return []


def decode_pdf417_text(image: Image.Image) -> list[str]:
    """Decode PDF417 barcode(s) and return as text strings.

    Args:
        image: PIL Image containing one or more PDF417 barcodes.

    Returns:
        List of decoded text strings, one per barcode found.
    """
    raw_payloads = decode_pdf417(image)
    return [payload.decode("latin-1") for payload in raw_payloads]
