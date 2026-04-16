"""Extract MRZ text from passport/PR card images using OCR.

Uses Tesseract via pytesseract with multi-strategy preprocessing.
Handles both clean rendered images and real-world photos.
"""

from __future__ import annotations

import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

_MRZ_CHARS = re.compile(r"[^A-Z0-9<]")
_MRZ_LINE_LOOSE = re.compile(r"[A-Z0-9<]{25,}")
_MRZ_START = re.compile(r"^[PIAC][A-Z<]")


def _clean_line(line: str) -> str:
    """Clean an OCR output line to valid MRZ characters."""
    line = line.upper().strip()
    line = line.replace(" ", "")
    line = line.replace("«", "<<")
    line = line.replace("\u00ab", "<<")
    line = line.replace("\u00bb", "<<")
    line = _MRZ_CHARS.sub("", line)
    return line


def _ocr_extract_lines(
    binary: np.ndarray,
    psm: int = 6,
) -> list[str]:
    """Run OCR and return cleaned MRZ-candidate lines."""
    config = f"--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
    raw = pytesseract.image_to_string(binary, config=config)
    lines = []
    for line in raw.split("\n"):
        cleaned = _clean_line(line)
        if len(cleaned) >= 25 and _MRZ_LINE_LOOSE.match(cleaned):
            lines.append(cleaned)
    return lines


def _ocr_no_whitelist(
    binary: np.ndarray,
    psm: int = 6,
) -> list[str]:
    """Run OCR without char whitelist, then clean.

    This often reads `<` better since Tesseract doesn't
    force it into the whitelist alphabet.
    """
    config = f"--psm {psm}"
    raw = pytesseract.image_to_string(binary, config=config)
    lines = []
    for line in raw.split("\n"):
        cleaned = _clean_line(line)
        if len(cleaned) >= 25 and _MRZ_LINE_LOOSE.match(cleaned):
            lines.append(cleaned)
    return lines


def _threshold_otsu(gray: np.ndarray) -> np.ndarray:
    """Otsu threshold."""
    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    return _ensure_dark_on_light(binary)


def _threshold_adaptive(gray: np.ndarray) -> np.ndarray:
    """Adaptive Gaussian threshold."""
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )
    return _ensure_dark_on_light(binary)


def _threshold_clahe(gray: np.ndarray) -> np.ndarray:
    """CLAHE enhanced + Otsu."""
    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8),
    )
    enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(
        enhanced,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    return _ensure_dark_on_light(binary)


def _ensure_dark_on_light(binary: np.ndarray) -> np.ndarray:
    """Ensure dark text on light background."""
    white_ratio = np.sum(binary > 127) / binary.size
    if white_ratio < 0.4:
        binary = cv2.bitwise_not(binary)
    return binary


def _scale_up(gray: np.ndarray, min_width: int = 1200) -> np.ndarray:
    """Scale image up if too small for OCR."""
    if gray.shape[1] < min_width:
        scale = min_width / gray.shape[1]
        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
    return gray


def _find_mrz_region(gray: np.ndarray) -> np.ndarray | None:
    """Find MRZ region via morphological detection."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    kernel_bh = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (13, 5),
    )
    blackhat = cv2.morphologyEx(
        blurred,
        cv2.MORPH_BLACKHAT,
        kernel_bh,
    )
    _, thresh = cv2.threshold(
        blackhat,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    kernel_close = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (21, 3),
    )
    closed = cv2.morphologyEx(
        thresh,
        cv2.MORPH_CLOSE,
        kernel_close,
    )
    kernel_v = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, 9),
    )
    closed = cv2.morphologyEx(
        closed,
        cv2.MORPH_CLOSE,
        kernel_v,
    )
    contours, _ = cv2.findContours(
        closed,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return None

    h, w = gray.shape
    candidates = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw >= w * 0.5 and ch >= h * 0.03:
            candidates.append((y / h, x, y, cw, ch))

    if not candidates:
        return None

    candidates.sort(key=lambda c: -c[0])
    _, x, y, cw, ch = candidates[0]
    pad_x = int(cw * 0.02)
    pad_y = int(ch * 0.3)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + cw + pad_x)
    y2 = min(h, y + ch + pad_y)
    return gray[y1:y2, x1:x2]


def _score_lines(lines: list[str]) -> float:
    """Score how likely lines are real MRZ."""
    if not lines:
        return 0.0

    score = 0.0
    if len(lines) in (2, 3):
        score += 2.0

    for line in lines:
        if "<<" in line:
            score += 3.0
            break

    if lines and _MRZ_START.match(lines[0]):
        score += 5.0

    for line in lines:
        if "CAN" in line[:10]:
            score += 3.0
            break

    lengths = [len(line) for line in lines]
    if (
        len(lines) == 2
        and all(42 <= line <= 46 for line in lengths)
        or len(lines) == 2
        and all(34 <= line <= 38 for line in lengths)
        or len(lines) == 3
        and all(28 <= line <= 32 for line in lengths)
    ):
        score += 4.0

    total_chevrons = sum(line.count("<") for line in lines)
    if total_chevrons > 10:
        score += 2.0

    return score


def _try_all_strategies(gray: np.ndarray) -> list[tuple]:
    """Try all OCR strategies on a grayscale image."""
    candidates = []
    scaled = _scale_up(gray)

    thresholds = [
        ("otsu", _threshold_otsu),
        ("adaptive", _threshold_adaptive),
        ("clahe", _threshold_clahe),
    ]
    psm_modes = [6, 4, 3]
    ocr_funcs = [
        ("whitelist", _ocr_extract_lines),
        ("no_whitelist", _ocr_no_whitelist),
    ]

    for _tname, tfunc in thresholds:
        binary = tfunc(scaled)
        for _oname, ofunc in ocr_funcs:
            for psm in psm_modes:
                lines = ofunc(binary, psm=psm)
                if lines:
                    score = _score_lines(lines)
                    candidates.append((score, lines))

    return candidates


def extract_mrz_from_image(
    image: Image.Image | np.ndarray,
) -> str | None:
    """Extract MRZ text from a passport or PR card image.

    Tries multiple strategies and picks the best result.
    """
    img_array = np.array(image.convert("RGB")) if isinstance(image, Image.Image) else image

    if len(img_array.shape) == 2:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    h = gray.shape[0]
    candidates = []

    # Strategy 1: Full image (works for clean rendered MRZ)
    candidates.extend(_try_all_strategies(gray))

    # Strategy 2: Morphological region detection
    mrz_region = _find_mrz_region(gray)
    if mrz_region is not None:
        candidates.extend(_try_all_strategies(mrz_region))

    # Strategy 3: Bottom crops
    for pct in (0.15, 0.25, 0.35, 0.50):
        crop = gray[int(h * (1 - pct)) :, :]
        candidates.extend(_try_all_strategies(crop))

    if not candidates:
        return None

    candidates.sort(key=lambda c: -c[0])
    best_lines = candidates[0][1]
    return _assemble_mrz(best_lines)


def _assemble_mrz(lines: list[str]) -> str | None:
    """Assemble MRZ lines into valid continuous string.

    IMPORTANT: preserves original OCR reading order (top to
    bottom). Never re-sorts lines — TD1 line order matters.
    """
    if len(lines) < 2:
        return None

    good = [line for line in lines if len(line) >= 25]
    if len(good) < 2:
        return None

    # TD1: 3x30 — keep original order
    td1 = [line for line in good if 28 <= len(line) <= 32]
    if len(td1) >= 3:
        return "".join(_pad(line, 30) for line in td1[:3])

    # TD3: 2x44 — keep original order
    td3 = [line for line in good if 42 <= len(line) <= 46]
    if len(td3) >= 2:
        return "".join(_pad(line, 44) for line in td3[:2])

    # TD2: 2x36 — keep original order
    td2 = [line for line in good if 34 <= len(line) <= 38]
    if len(td2) >= 2:
        return "".join(_pad(line, 36) for line in td2[:2])

    # Fallback: concatenate in order
    combined = "".join(good)
    if len(combined) in (88, 90, 72):
        return combined

    # Last resort: take first 2-3 lines in order
    if len(good) >= 3:
        return "".join(_pad(line, 30) for line in good[:3])
    if len(good) >= 2:
        return "".join(_pad(line, 44) for line in good[:2])

    return None


def _pad(line: str, length: int) -> str:
    """Pad or trim a line to exact length."""
    if len(line) < length:
        line += "<" * (length - len(line))
    return line[:length]
