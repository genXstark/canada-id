"""Context-aware OCR correction engine.

Fixes common OCR misreads by mapping visually similar characters.
Corrections are context-dependent: date fields get letter-to-digit,
name fields get digit-to-letter. Ported from MRZParser-develop.
"""
from __future__ import annotations

_LETTER_TO_DIGIT: dict[str, str] = {
    "O": "0",
    "Q": "0",
    "U": "0",
    "D": "0",
    "I": "1",
    "Z": "2",
    "B": "8",
}

_DIGIT_TO_LETTER: dict[str, str] = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "8": "B",
}

_SEX_CORRECTIONS: dict[str, str] = {
    "P": "F",
}


def correct_date(text: str) -> str:
    """OCR-correct a date or check-digit field (digits only)."""
    return "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in text)


def correct_alpha(text: str) -> str:
    """OCR-correct a purely alphabetic field (names, countries)."""
    return "".join(_DIGIT_TO_LETTER.get(ch, ch) for ch in text)


def correct_sex(text: str) -> str:
    """OCR-correct a sex field."""
    return _SEX_CORRECTIONS.get(text, text)
