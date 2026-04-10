"""PDF417 barcode encoder.

Ported from AAMVA-to-PDF417-Generator (JavaScript), which was
ported from TCPDF's PHP PDF417 class.  Uses Python's native
arbitrary-precision integers instead of bcmath.
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from canada_id.codec.tables import (
    CLUSTERS,
    QUIETH,
    QUIETV,
    ROWHEIGHT,
    RS_FACTORS,
    START_PATTERN,
    STOP_PATTERN,
    TEXT_LATCH,
    TEXT_SUBMODES,
)

if TYPE_CHECKING:
    from PIL import Image


# ── Public API ───────────────────────────────────────────


def encode_pdf417(
    data: str | bytes,
    ecl: int = -1,
    aspect_ratio: float = 2.0,
) -> list[list[int]]:
    """Encode *data* as a PDF417 barcode.

    Args:
        data: The string (or raw bytes) to encode.
        ecl: Error correction level 0-8, or -1 for automatic.
        aspect_ratio: Target width-to-height ratio (excluding
            quiet zones).

    Returns:
        2-D list of ints (0/1) representing the barcode bitmap.
    """
    if isinstance(data, bytes):
        code = data.decode("latin-1")
    else:
        # AAMVA uses Latin-1 (ISO 8859-1). Encode directly to Latin-1
        # to preserve accented characters like É, È, Ê as single bytes.
        # Previous UTF-8 encoding caused mojibake (É → Ã‰).
        code = data.encode("latin-1").decode("latin-1")

    if not code:
        return []

    sequence = _get_input_sequences(code)
    codewords: list[int] = []
    for mode, segment in sequence:
        codewords.extend(_get_compaction(mode, segment))

    if codewords and codewords[0] == 900:
        codewords.pop(0)

    num_cw = len(codewords)
    if num_cw > 925:
        return []

    ecl = _get_error_correction_level(ecl, num_cw)
    err_size = 2 << ecl

    cols, rows, size = _calc_dimensions(
        num_cw, err_size, aspect_ratio,
    )

    pad = size - (num_cw + err_size + 1)
    if pad > 0:
        if size - rows == num_cw + err_size + 1:
            rows -= 1
            size -= rows
        else:
            codewords.extend([900] * pad)

    sld = size - err_size
    codewords.insert(0, sld)

    ecw = _get_error_correction(codewords, ecl)
    codewords.extend(ecw)

    return _render_barcode(codewords, cols, rows, ecl)


def barcode_to_image(
    barcode: list[list[int]],
    scale: int = 2,
) -> Image:
    """Convert a 2-D bit array to a PIL Image.

    Args:
        barcode: Output of :func:`encode_pdf417`.
        scale: Pixel multiplier (1 = 1 module per pixel).

    Returns:
        A ``PIL.Image.Image`` in mode ``"1"``.
    """
    from PIL import Image as PILImage

    if not barcode:
        return PILImage.new("1", (1, 1), 1)

    h = len(barcode)
    w = len(barcode[0])
    img = PILImage.new("1", (w * scale, h * scale), 1)
    pixels = img.load()
    for y, row in enumerate(barcode):
        for x, val in enumerate(row):
            if val:
                for sy in range(scale):
                    for sx in range(scale):
                        pixels[x * scale + sx, y * scale + sy] = 0
    return img


# ── Dimension calculation ────────────────────────────────


def _calc_dimensions(
    num_cw: int, err_size: int, aspect_ratio: float,
) -> tuple[int, int, int]:
    """Return (cols, rows, size) for the symbol."""
    nce = num_cw + err_size + 1
    cols = round(
        (math.sqrt(4761 + 68 * aspect_ratio * ROWHEIGHT * nce)
         - 69) / 34
    )
    cols = max(1, min(cols, 30))
    rows = math.ceil(nce / cols)
    size = cols * rows

    if rows < 3 or rows > 90:
        rows = max(3, min(rows, 90))
        cols = math.ceil(size / rows)
        size = cols * rows

    if size > 928:
        d1 = abs(aspect_ratio - (17 * 29 / 32))
        d2 = abs(aspect_ratio - (17 * 16 / 58))
        if d1 < d2:
            cols, rows = 29, 32
        else:
            cols, rows = 16, 58
        size = 928

    return cols, rows, size


# ── Input sequence splitting ─────────────────────────────


def _get_input_sequences(
    code: str,
) -> list[tuple[int, str]]:
    """Split *code* into (mode, segment) pairs.

    Modes: 900=text, 901/924=byte, 902=numeric, 913=byte-shift.
    """
    sequence: list[tuple[int, str]] = []

    num_runs: list[tuple[str, int]] = []
    for m in re.finditer(r"[0-9]{13,44}", code):
        num_runs.append((m.group(), m.start()))
    num_runs.append(("", len(code)))

    offset = 0
    for num_str, num_pos in num_runs:
        if num_pos > offset:
            prev = code[offset:num_pos]
            _extract_text_byte(prev, sequence)
        if num_str:
            sequence.append((902, num_str))
        offset = num_pos + len(num_str)

    return sequence


def _extract_text_byte(
    prev: str,
    sequence: list[tuple[int, str]],
) -> None:
    """Extract text and byte sub-sequences from *prev*."""
    text_runs: list[tuple[str, int]] = []
    for m in re.finditer(
        r"[\x09\x0a\x0d\x20-\x7e]{5,}", prev,
    ):
        text_runs.append((m.group(), m.start()))
    text_runs.append(("", len(prev)))

    txt_offset = 0
    for txt_str, txt_pos in text_runs:
        if txt_pos > txt_offset:
            byte_seg = prev[txt_offset:txt_pos]
            if len(byte_seg) == 1 and sequence and sequence[-1][0] == 900:
                sequence.append((913, byte_seg))
            elif len(byte_seg) % 6 == 0:
                sequence.append((924, byte_seg))
            else:
                sequence.append((901, byte_seg))
        if txt_str:
            sequence.append((900, txt_str))
        txt_offset = txt_pos + len(txt_str)


# ── Compaction modes ─────────────────────────────────────


def _get_compaction(mode: int, code: str) -> list[int]:
    """Convert a segment to codewords (including mode latch)."""
    if mode == 900:
        cw = _text_compaction(code)
    elif mode in (901, 924):
        cw = _byte_compaction(code, mode)
    elif mode == 902:
        cw = _numeric_compaction(code)
    elif mode == 913:
        cw = [ord(code[0])] if code else []
    else:
        cw = []
    cw.insert(0, mode)
    return cw


def _text_compaction(code: str) -> list[int]:
    """Encode text using sub-mode switching."""
    submode = 0
    txt_arr: list[int] = []

    for i, ch in enumerate(code):
        chval = ord(ch)
        k = _index_of(chval, TEXT_SUBMODES[submode])
        if k is not None:
            txt_arr.append(k)
            continue
        for s in range(4):
            if s == submode:
                continue
            k = _index_of(chval, TEXT_SUBMODES[s])
            if k is None:
                continue
            next_in_cur = (
                i + 1 < len(code)
                and _index_of(
                    ord(code[i + 1]), TEXT_SUBMODES[submode],
                ) is not None
            )
            is_last = i + 1 == len(code)
            if (is_last or next_in_cur) and (
                s == 3 or (s == 0 and submode == 1)
            ):
                txt_arr.append(29 if s == 3 else 27)
            else:
                key = f"{submode}{s}"
                txt_arr.extend(TEXT_LATCH[key])
                submode = s
            txt_arr.append(k)
            break

    if len(txt_arr) % 2 != 0:
        txt_arr.append(29)

    cw: list[int] = []
    for i in range(0, len(txt_arr), 2):
        cw.append(30 * txt_arr[i] + txt_arr[i + 1])
    return cw


def _byte_compaction(code: str, mode: int) -> list[int]:
    """Encode bytes; 6-byte blocks use base-256-to-base-900."""
    cw: list[int] = []
    while code:
        if len(code) > 6:
            block, code = code[:6], code[6:]
        else:
            block, code = code, ""

        if len(block) == 6:
            t = (
                ord(block[0]) * 1099511627776
                + ord(block[1]) * 4294967296
                + ord(block[2]) * 16777216
                + ord(block[3]) * 65536
                + ord(block[4]) * 256
                + ord(block[5])
            )
            cw6: list[int] = []
            while t > 0:
                cw6.insert(0, t % 900)
                t //= 900
            cw.extend(cw6)
        else:
            for ch in block:
                cw.append(ord(ch))
    return cw


def _numeric_compaction(code: str) -> list[int]:
    """Encode digit strings; chunks of up to 44 digits."""
    cw: list[int] = []
    while code:
        if len(code) > 44:
            chunk, code = code[:44], code[44:]
        else:
            chunk, code = code, ""
        t = int("1" + chunk)
        segment: list[int] = []
        while t > 0:
            segment.insert(0, t % 900)
            t //= 900
        cw.extend(segment)
    return cw


# ── Error correction ─────────────────────────────────────


def _get_error_correction_level(
    ecl: int, num_cw: int,
) -> int:
    """Select ECL automatically if *ecl* < 0 or > 8."""
    max_ecl = 8
    max_err = 928 - num_cw
    while max_ecl > 0:
        # JS: 2 << negative wraps to 0, so this always breaks
        # when ecl < 0.  Guard the same way here.
        err_need = (2 << ecl) if ecl >= 0 else 0
        if max_err >= err_need:
            break
        max_ecl -= 1

    if ecl < 0 or ecl > 8:
        if num_cw < 41:
            ecl = 2
        elif num_cw < 161:
            ecl = 3
        elif num_cw < 321:
            ecl = 4
        elif num_cw < 864:
            ecl = 5
        else:
            ecl = max_ecl

    return min(ecl, max_ecl)


def _get_error_correction(
    cw: list[int], ecl: int,
) -> list[int]:
    """Compute Reed-Solomon error-correction codewords."""
    ecc = RS_FACTORS[ecl]
    ecl_size = 2 << ecl
    ecl_max = ecl_size - 1
    ecw = [0] * ecl_size

    for val in cw:
        t1 = (val + ecw[ecl_max]) % 929
        for j in range(ecl_max, 0, -1):
            t2 = (t1 * ecc[j]) % 929
            ecw[j] = (ecw[j - 1] + 929 - t2) % 929
        t2 = (t1 * ecc[0]) % 929
        ecw[0] = (929 - t2) % 929

    ecw = [929 - v if v != 0 else 0 for v in ecw]
    ecw.reverse()
    return ecw


# ── Barcode rendering ────────────────────────────────────


def _render_barcode(
    codewords: list[int],
    cols: int,
    rows: int,
    ecl: int,
) -> list[list[int]]:
    """Build the final 2-D bit matrix."""
    num_cols = (cols + 2) * 17 + 35 + 2 * QUIETH
    pstart = "0" * QUIETH + START_PATTERN
    pstop = STOP_PATTERN + "0" * QUIETH

    barcode: list[list[int]] = []

    empty_row = [0] * num_cols
    for _ in range(QUIETV):
        barcode.append(list(empty_row))

    k = 0
    cid = 0
    for r in range(rows):
        row_bits = pstart
        left_l = _left_indicator(r, rows, cols, ecl, cid)
        row_bits += format(CLUSTERS[cid][left_l], "017b")

        for _ in range(cols):
            row_bits += format(
                CLUSTERS[cid][codewords[k]], "017b",
            )
            k += 1

        right_l = _right_indicator(r, rows, cols, ecl, cid)
        row_bits += format(CLUSTERS[cid][right_l], "017b")
        row_bits += pstop

        arow = [int(c) for c in row_bits]
        for _ in range(ROWHEIGHT):
            barcode.append(list(arow))

        cid = (cid + 1) % 3

    for _ in range(QUIETV):
        barcode.append(list(empty_row))

    return barcode


def _left_indicator(
    r: int, rows: int, cols: int, ecl: int, cid: int,
) -> int:
    """Compute left row-indicator codeword index."""
    base = 30 * (r // 3)
    if cid == 0:
        return base + (rows - 1) // 3
    if cid == 1:
        return base + ecl * 3 + (rows - 1) % 3
    return base + cols - 1


def _right_indicator(
    r: int, rows: int, cols: int, ecl: int, cid: int,
) -> int:
    """Compute right row-indicator codeword index."""
    base = 30 * (r // 3)
    if cid == 0:
        return base + cols - 1
    if cid == 1:
        return base + (rows - 1) // 3
    return base + ecl * 3 + (rows - 1) % 3


# ── Helpers ──────────────────────────────────────────────


def _index_of(val: int, arr: list[int]) -> int | None:
    """Return index of *val* in *arr*, or ``None``."""
    try:
        return arr.index(val)
    except ValueError:
        return None
