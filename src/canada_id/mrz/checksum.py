"""ICAO 9303 check-digit calculation.

Weighted-sum algorithm (weights 7, 3, 1) used across all MRZ
formats for document-number, date, and composite check digits.
Ported from MRZParser-develop with verify_extended for ICAO Note j.
"""

from __future__ import annotations

_WEIGHTS = (7, 3, 1)

_CHAR_VALUE: dict[str, int] = {}
for _c in "0123456789":
    _CHAR_VALUE[_c] = int(_c)
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _CHAR_VALUE[_c] = _i + 10
_CHAR_VALUE["<"] = 0


def compute(text: str) -> int:
    """Return the ICAO 9303 check digit (0-9) for *text*.

    Raises ``ValueError`` on invalid characters.
    """
    total = 0
    for i, ch in enumerate(text):
        val = _CHAR_VALUE.get(ch)
        if val is None:
            raise ValueError(f"Invalid MRZ character: {ch!r} at position {i}")
        total += val * _WEIGHTS[i % 3]
    return total % 10


def compute_str(text: str) -> str:
    """Return the check digit as a single-character string."""
    return str(compute(text))


def verify(text: str, expected: str) -> bool:
    """Return True when the check digit of *text* equals *expected*."""
    if not expected or len(expected) != 1:
        return False
    exp_val = _CHAR_VALUE.get(expected)
    if exp_val is None:
        return False
    try:
        return compute(text) == exp_val
    except ValueError:
        return False


def verify_extended(
    doc_number: str,
    doc_check: str,
    optional_data: str | None,
) -> bool:
    """Verify a possibly-extended document number (ICAO Note j).

    When the check digit field is '<' and the optional-data field
    contains the real check digit, the document number overflows
    into optional data.
    """
    if verify(doc_number, doc_check):
        return True

    if doc_check != "<" or not optional_data or len(optional_data) < 2:
        return False

    sep = optional_data.find("<")
    if sep < 2:
        return False

    real_check = optional_data[sep - 1]
    ext = optional_data[: sep - 1]

    return verify(doc_number + "<" + ext, real_check) or verify(doc_number + ext, real_check)
