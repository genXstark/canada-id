"""Public API for PDF417 barcode decoding."""
from PIL import Image

from canada_id.codec._pdf417dec.Decoder import PDF417Decoder


def _ensure_rgb(image: Image.Image) -> Image.Image:
    """Convert image to RGB if needed (decoder requires it)."""
    if image.mode not in ("RGB", "L"):
        return image.convert("RGB")
    return image


def decode_pdf417(image: Image.Image) -> list[bytes]:
    """Decode PDF417 barcode(s) from a PIL Image.

    Args:
        image: PIL Image containing one or more PDF417 barcodes.

    Returns:
        List of decoded byte payloads, one per barcode found.
    """
    image = _ensure_rgb(image)
    decoder = PDF417Decoder(image)
    count = decoder.decode()
    if count == 0:
        return []
    return [bytes(info.barcode_data) for info in decoder.barcodes_info]


def decode_pdf417_text(image: Image.Image) -> list[str]:
    """Decode PDF417 barcode(s) and return as text strings.

    Args:
        image: PIL Image containing one or more PDF417 barcodes.

    Returns:
        List of decoded text strings, one per barcode found.
    """
    raw_payloads = decode_pdf417(image)
    return [payload.decode("latin-1") for payload in raw_payloads]
