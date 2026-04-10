"""Extract MRZ text from passport/PR card images using OCR.

Uses Tesseract via pytesseract with preprocessing optimized
for the MRZ zone (bottom of card/passport).
"""
from __future__ import annotations

import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

_MRZ_CHARS = re.compile(r"[^A-Z0-9<]")
_MRZ_LINE = re.compile(r"[A-Z0-9<]{28,44}")


def _preprocess_for_mrz(image: np.ndarray) -> np.ndarray:
    """Preprocess image to isolate MRZ zone."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Take bottom 40% of image (MRZ is always at bottom)
    h = gray.shape[0]
    bottom = gray[int(h * 0.5):, :]

    # Resize for better OCR (scale up if small)
    if bottom.shape[1] < 1000:
        scale = 1000 / bottom.shape[1]
        bottom = cv2.resize(
            bottom, None, fx=scale, fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    # Sharpen
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(bottom, -1, kernel)

    # Threshold to binary (black text on white bg)
    _, binary = cv2.threshold(
        sharpened, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    # Invert if background is dark (white text on dark)
    white_ratio = np.sum(binary > 127) / binary.size
    if white_ratio < 0.5:
        binary = cv2.bitwise_not(binary)

    return binary


def _clean_ocr_line(line: str) -> str:
    """Clean an OCR output line to valid MRZ characters."""
    line = line.upper().strip()
    # Common OCR substitutions
    line = line.replace(" ", "")
    line = line.replace("«", "<<")
    line = line.replace("K<", "K<")
    line = _MRZ_CHARS.sub("", line)
    return line


def extract_mrz_from_image(
    image: Image.Image | np.ndarray,
) -> str | None:
    """Extract MRZ text from a passport or PR card image.

    Args:
        image: PIL Image or numpy array of the document.

    Returns:
        MRZ string (continuous, no newlines) or None if not found.
    """
    if isinstance(image, Image.Image):
        img_array = np.array(image.convert("RGB"))
    else:
        img_array = image

    if len(img_array.shape) == 2:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

    processed = _preprocess_for_mrz(img_array)

    # OCR with MRZ-optimized config
    ocr_config = (
        "--psm 6 -c tessedit_char_whitelist="
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
    )
    raw_text = pytesseract.image_to_string(
        processed, config=ocr_config,
    )

    # Extract valid MRZ lines
    mrz_lines = []
    for line in raw_text.split("\n"):
        cleaned = _clean_ocr_line(line)
        if _MRZ_LINE.match(cleaned):
            mrz_lines.append(cleaned)

    if not mrz_lines:
        # Try full image (not just bottom half)
        raw_full = pytesseract.image_to_string(
            _preprocess_full(img_array), config=ocr_config,
        )
        for line in raw_full.split("\n"):
            cleaned = _clean_ocr_line(line)
            if _MRZ_LINE.match(cleaned):
                mrz_lines.append(cleaned)

    if not mrz_lines:
        return None

    return _assemble_mrz(mrz_lines)


def _preprocess_full(image: np.ndarray) -> np.ndarray:
    """Preprocess full image for OCR fallback."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.shape[1] < 1000:
        scale = 1000 / gray.shape[1]
        gray = cv2.resize(
            gray, None, fx=scale, fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
    _, binary = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    white_ratio = np.sum(binary > 127) / binary.size
    if white_ratio < 0.5:
        binary = cv2.bitwise_not(binary)
    return binary


def _assemble_mrz(lines: list[str]) -> str | None:
    """Assemble MRZ lines into a valid continuous string.

    Detects TD1 (3x30), TD2 (2x36), TD3 (2x44) by line lengths.
    Pads/trims lines to expected lengths.
    """
    if len(lines) < 2:
        return None

    # Try to detect format from line lengths
    avg_len = sum(len(l) for l in lines) / len(lines)

    if len(lines) >= 3 and 28 <= avg_len <= 32:
        # TD1: 3 x 30
        padded = [_pad_line(l, 30) for l in lines[:3]]
        return "".join(padded)

    if len(lines) >= 2 and 42 <= avg_len <= 46:
        # TD3: 2 x 44
        padded = [_pad_line(l, 44) for l in lines[:2]]
        return "".join(padded)

    if len(lines) >= 2 and 34 <= avg_len <= 38:
        # TD2: 2 x 36
        padded = [_pad_line(l, 36) for l in lines[:2]]
        return "".join(padded)

    # Fallback: try exact lengths
    if len(lines) >= 3:
        td1 = "".join(_pad_line(l, 30) for l in lines[:3])
        if len(td1) == 90:
            return td1

    if len(lines) >= 2:
        combined = "".join(lines[:2])
        if len(combined) == 88:
            return combined
        if len(combined) == 72:
            return combined

    # Last resort: concatenate and hope
    combined = "".join(lines)
    if len(combined) in (90, 72, 88):
        return combined

    return None


def _pad_line(line: str, length: int) -> str:
    """Pad or trim a line to exact length."""
    if len(line) < length:
        line += "<" * (length - len(line))
    return line[:length]
