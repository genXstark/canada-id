"""Shared utility functions for MRZ processing.

Ported from MRZParser-develop.
"""

from __future__ import annotations

import re
from datetime import date

_INVALID_CHARS = re.compile(r"[^A-Z0-9<]")


def purify(text: str) -> str:
    """Strip all non-MRZ characters from *text*."""
    return _INVALID_CHARS.sub("", text.upper())


def pad(text: str | None, length: int, filler: str = "<") -> str:
    """Right-pad *text* with *filler* to exactly *length* chars."""
    text = text or ""
    if len(text) < length:
        text += filler * (length - len(text))
    return text[:length]


def unpad(text: str | None) -> str:
    """Remove filler characters and trim."""
    if text is None:
        return ""
    return text.replace("<", " ").strip()


def split_names(text: str) -> tuple[str, str]:
    """Split MRZ name field into (surname, given_names).

    Names are separated by '<<'; individual given names by '<'.
    """
    parts = text.split("<<", 1)
    primary = unpad(parts[0])
    secondary = unpad(parts[1]) if len(parts) > 1 else ""
    return primary, secondary


def encode_name(surname: str, given_names: str, length: int) -> str:
    """Encode surname + given names into MRZ name field."""
    surname_mrz = surname.upper().replace(" ", "<").replace("-", "<")
    given_mrz = given_names.upper().replace(" ", "<").replace("-", "<")
    combined = surname_mrz + "<<" + given_mrz
    return pad(combined, length)


def parse_mrz_date(
    yymmdd: str,
    is_birth: bool = True,
) -> date | None:
    """Convert YYMMDD string to date object.

    For birth dates, years > current 2-digit year assume 1900s.
    For expiry dates, 50-year window heuristic.
    """
    if not yymmdd or len(yymmdd) < 6 or yymmdd.strip("<") == "":
        return None
    try:
        yy = int(yymmdd[0:2])
        mm = int(yymmdd[2:4])
        dd = int(yymmdd[4:6])
    except ValueError:
        return None
    if mm == 0 or dd == 0:
        return None

    current_year_2 = date.today().year % 100
    if is_birth:
        century = 1900 if yy > current_year_2 else 2000
    else:
        century = 2000 if yy <= (current_year_2 + 50) % 100 else 1900

    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


def lines_from_mrz(text: str) -> list[str]:
    """Split an MRZ string into lines (handles newlines or continuous)."""
    text = text.strip()
    if "\n" in text:
        return [line.strip() for line in text.split("\n") if line.strip()]

    n = len(text)
    if n == 90:
        return [text[0:30], text[30:60], text[60:90]]
    if n == 72:
        return [text[0:36], text[36:72]]
    if n == 88:
        return [text[0:44], text[44:88]]
    return [text]
