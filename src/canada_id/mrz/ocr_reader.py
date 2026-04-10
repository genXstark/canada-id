"""Extract MRZ text from passport/PR card images using OCR.

Uses Tesseract via pytesseract with multi-strategy preprocessing:
1. Morphological MRZ region detection (finds the dense text block)
2. Progressive crop from bottom (10%, 20%, 30%, 50%)
3. Multiple threshold and contrast strategies per crop

Handles real-world photos: angled, noisy, mixed pages.
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

# MRZ lines are exactly 30, 36, or 44 chars
_MRZ_LINE_STRICT = re.compile(r"^[A-Z0-9<]{29,45}$")

# Looser match for initial filtering
_MRZ_LINE_LOOSE = re.compile(r"[A-Z0-9<]{25,}")

# MRZ always starts with known doc type prefixes
_MRZ_START = re.compile(
    r"^[PIAC][A-Z<]"
)

_OCR_CONFIG = (
    "--psm 6 -c tessedit_char_whitelist="
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
)

_OCR_CONFIG_SINGLE = (
    "--psm 7 -c tessedit_char_whitelist="
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
)


def _clean_line(line: str) -> str:
    """Clean an OCR output line to valid MRZ characters."""
    line = line.upper().strip()
    line = line.replace(" ", "")
    line = line.replace("«", "<<")
    line = line.replace("\u00ab", "<<")
    line = line.replace("\u00bb", "<<")
    line = _MRZ_CHARS.sub("", line)
    return line


def _find_mrz_region(gray: np.ndarray) -> np.ndarray | None:
    """Find MRZ region using morphological operations.

    MRZ text is a dense horizontal block of dark characters
    on light background. We detect it by:
    1. Blackhat morphology to find dark text on light bg
    2. Horizontal closing to merge chars into lines
    3. Find contours that span most of the image width
    """
    # Smooth to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Blackhat: find dark regions (text) on light bg
    kernel_bh = cv2.getStructuringElement(
        cv2.MORPH_RECT, (13, 5),
    )
    blackhat = cv2.morphologyEx(
        blurred, cv2.MORPH_BLACKHAT, kernel_bh,
    )

    # Threshold the blackhat result
    _, thresh = cv2.threshold(
        blackhat, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    # Close horizontally to merge characters into lines
    kernel_close = cv2.getStructuringElement(
        cv2.MORPH_RECT, (21, 3),
    )
    closed = cv2.morphologyEx(
        thresh, cv2.MORPH_CLOSE, kernel_close,
    )

    # Close vertically to merge MRZ lines together
    kernel_v = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, 9),
    )
    closed = cv2.morphologyEx(
        closed, cv2.MORPH_CLOSE, kernel_v,
    )

    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    h, w = gray.shape
    min_width = w * 0.5
    min_height = h * 0.03

    candidates = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw >= min_width and ch >= min_height:
            # Prefer regions in the bottom half
            bottom_score = y / h
            candidates.append((bottom_score, x, y, cw, ch))

    if not candidates:
        return None

    # Pick the lowest (most bottom) wide region
    candidates.sort(key=lambda c: -c[0])
    _, x, y, cw, ch = candidates[0]

    # Add padding
    pad_x = int(cw * 0.02)
    pad_y = int(ch * 0.3)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + cw + pad_x)
    y2 = min(h, y + ch + pad_y)

    return gray[y1:y2, x1:x2]


def _prepare_for_ocr(
    gray: np.ndarray, method: str = "otsu",
) -> np.ndarray:
    """Prepare a grayscale crop for OCR with given method."""
    # Scale up if small
    if gray.shape[1] < 1200:
        scale = 1200 / gray.shape[1]
        gray = cv2.resize(
            gray, None, fx=scale, fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    if method == "otsu":
        _, binary = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
    elif method == "adaptive":
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10,
        )
    elif method == "high_contrast":
        # CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(
            clipLimit=3.0, tileGridSize=(8, 8),
        )
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(
            enhanced, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
    else:
        _, binary = cv2.threshold(
            gray, 127, 255, cv2.THRESH_BINARY,
        )

    # Ensure black text on white bg
    white_ratio = np.sum(binary > 127) / binary.size
    if white_ratio < 0.4:
        binary = cv2.bitwise_not(binary)

    return binary


def _ocr_and_extract(binary: np.ndarray) -> list[str]:
    """Run OCR on binary image, return cleaned MRZ-like lines."""
    raw = pytesseract.image_to_string(
        binary, config=_OCR_CONFIG,
    )

    lines = []
    for line in raw.split("\n"):
        cleaned = _clean_line(line)
        if len(cleaned) >= 25 and _MRZ_LINE_LOOSE.match(cleaned):
            lines.append(cleaned)

    return lines


def _score_mrz_lines(lines: list[str]) -> float:
    """Score how likely these lines are real MRZ."""
    if not lines:
        return 0.0

    score = 0.0

    # Check line count (2 or 3)
    if len(lines) in (2, 3):
        score += 2.0

    # Check for << separators (names always have <<)
    for line in lines:
        if "<<" in line:
            score += 3.0
            break

    # Check first line starts with doc type
    if lines and _MRZ_START.match(lines[0]):
        score += 5.0

    # Check for CAN (Canadian document)
    for line in lines:
        if "CAN" in line[:10]:
            score += 3.0
            break

    # Check line lengths are consistent
    lengths = [len(l) for l in lines]
    if len(lines) == 2 and all(42 <= l <= 46 for l in lengths):
        score += 4.0  # TD3
    elif len(lines) == 2 and all(34 <= l <= 38 for l in lengths):
        score += 4.0  # TD2
    elif len(lines) == 3 and all(28 <= l <= 32 for l in lengths):
        score += 4.0  # TD1

    # Penalize lines with too few < chars (MRZ always has fillers)
    total_chevrons = sum(l.count("<") for l in lines)
    if total_chevrons > 10:
        score += 2.0

    return score


def extract_mrz_from_image(
    image: Image.Image | np.ndarray,
) -> str | None:
    """Extract MRZ text from a passport or PR card image.

    Tries multiple strategies:
    1. Morphological MRZ region detection
    2. Bottom crops at 15%, 25%, 35%, 50%
    3. For each crop, tries 3 threshold methods

    Returns the best-scoring MRZ found.
    """
    if isinstance(image, Image.Image):
        img_array = np.array(image.convert("RGB"))
    else:
        img_array = image

    if len(img_array.shape) == 2:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    h = gray.shape[0]

    # Collect all candidate extractions with scores
    candidates = []

    # Strategy 1: Morphological region detection
    mrz_region = _find_mrz_region(gray)
    if mrz_region is not None:
        for method in ("otsu", "adaptive", "high_contrast"):
            binary = _prepare_for_ocr(mrz_region, method)
            lines = _ocr_and_extract(binary)
            if lines:
                score = _score_mrz_lines(lines)
                candidates.append((score, lines))

    # Strategy 2: Progressive bottom crops
    for pct in (0.15, 0.25, 0.35, 0.50):
        crop = gray[int(h * (1 - pct)):, :]
        for method in ("otsu", "adaptive", "high_contrast"):
            binary = _prepare_for_ocr(crop, method)
            lines = _ocr_and_extract(binary)
            if lines:
                score = _score_mrz_lines(lines)
                candidates.append((score, lines))

    if not candidates:
        return None

    # Pick the best scoring candidate
    candidates.sort(key=lambda c: -c[0])
    best_lines = candidates[0][1]

    return _assemble_mrz(best_lines)


def _assemble_mrz(lines: list[str]) -> str | None:
    """Assemble MRZ lines into valid continuous string."""
    if len(lines) < 2:
        return None

    # Filter to keep only the best lines
    # Sort by length descending, take the ones that look like MRZ
    good_lines = []
    for line in lines:
        if len(line) >= 25:
            good_lines.append(line)

    if len(good_lines) < 2:
        return None

    # Try to find TD3 first (passport, 2x44) — most common
    td3_lines = [l for l in good_lines if 42 <= len(l) <= 46]
    if len(td3_lines) >= 2:
        # Pick the 2 with best MRZ characteristics
        td3_lines = _pick_best_lines(td3_lines, 2)
        padded = [_pad_line(l, 44) for l in td3_lines[:2]]
        return "".join(padded)

    # Try TD1 (PR card, 3x30)
    td1_lines = [l for l in good_lines if 28 <= len(l) <= 32]
    if len(td1_lines) >= 3:
        td1_lines = _pick_best_lines(td1_lines, 3)
        padded = [_pad_line(l, 30) for l in td1_lines[:3]]
        return "".join(padded)

    # Try TD2 (2x36)
    td2_lines = [l for l in good_lines if 34 <= len(l) <= 38]
    if len(td2_lines) >= 2:
        td2_lines = _pick_best_lines(td2_lines, 2)
        padded = [_pad_line(l, 36) for l in td2_lines[:2]]
        return "".join(padded)

    # Fallback: try concatenating and see if total is valid
    combined = "".join(good_lines)
    if len(combined) in (88, 90, 72):
        return combined

    # Last resort: take 2 longest lines as TD3
    good_lines.sort(key=len, reverse=True)
    if len(good_lines) >= 2:
        top2 = good_lines[:2]
        padded = [_pad_line(l, 44) for l in top2]
        return "".join(padded)

    return None


def _pick_best_lines(
    lines: list[str], count: int,
) -> list[str]:
    """Pick the best N lines based on MRZ characteristics."""
    scored = []
    for line in lines:
        s = 0.0
        if "<<" in line:
            s += 3.0
        if _MRZ_START.match(line):
            s += 5.0
        if "CAN" in line[:10]:
            s += 2.0
        s += line.count("<") * 0.1
        scored.append((s, line))

    scored.sort(key=lambda x: -x[0])
    return [line for _, line in scored[:count]]


def _pad_line(line: str, length: int) -> str:
    """Pad or trim a line to exact length."""
    if len(line) < length:
        line += "<" * (length - len(line))
    return line[:length]
