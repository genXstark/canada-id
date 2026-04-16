"""MRZ parsers for TD1, TD2, TD3 formats (Canada-only).

Regex-based field extraction with ICAO 9303 check digit validation.
Ported from MRZParser-develop, stripped of French/Belgian/visa formats.
"""
from __future__ import annotations

import re

from canada_id.mrz import checksum, ocr
from canada_id.mrz.models import MrzFormat, MrzResult, Sex
from canada_id.mrz.utils import parse_mrz_date, split_names, unpad


class MrzParseError(Exception):
    """Raised when MRZ text cannot be parsed."""


def detect_format(text: str) -> MrzFormat:
    """Detect MRZ format from total text length."""
    n = len(text)
    if n == 90:
        return MrzFormat.TD1
    if n == 72:
        return MrzFormat.TD2
    if n == 88:
        return MrzFormat.TD3
    raise MrzParseError(
        f"Cannot detect MRZ format: got {n} characters"
        f" (expected 90 for TD1, 72 for TD2, or 88 for TD3)."
        f" Make sure you're pasting the raw MRZ lines"
        f" (the <<< text), not the parsed field summary."
    )


# Letters commonly OCR-misread as < filler
_FILLER_MISREADS = re.compile(r"[K]{3,}")


def _fix_ocr_fillers(text: str) -> str:
    """Replace runs of letters that OCR misread as < fillers.

    Tesseract commonly reads < as K, C, or similar.
    Runs of 3+ identical letters in filler positions
    are almost certainly meant to be <.
    """
    return _FILLER_MISREADS.sub(
        lambda m: "<" * len(m.group(0)), text,
    )


_MRZ_LINE = re.compile(r"[A-Z0-9<]{28,46}")


def _extract_mrz_lines(text: str) -> str | None:
    """Try to extract valid MRZ lines from noisy text.

    Looks for lines of 30, 36, or 44 MRZ-valid characters.
    Returns cleaned MRZ string if a valid set is found.
    """
    lines = _MRZ_LINE.findall(text)
    if not lines:
        return None

    # Group by expected line length
    for line_len, count in [(30, 3), (44, 2), (36, 2)]:
        matching = [ln for ln in lines if len(ln) == line_len]
        if len(matching) >= count:
            return "".join(matching[:count])

    return None


# ── TD1: 3 x 30 ────────────────────────────────────────

_TD1_LINE1 = re.compile(
    r"([A-Z0-9<]{2})"
    r"([A-Z<]{3})"
    r"([A-Z0-9<]{9})"
    r"([0-9<]{1})"
    r"([A-Z0-9<]{15})"
)

_TD1_LINE2 = re.compile(
    r"([0-9<]{6})"
    r"([0-9<]{1})"
    r"([MFX<]{1})"
    r"([0-9<]{6})"
    r"([0-9<]{1})"
    r"([A-Z<]{3})"
    r"([A-Z0-9<]{11})"
    r"([0-9<]{1})"
)

_TD1_LINE3 = re.compile(r"([A-Z0-9<]{30})")


def parse_td1(text: str, *, ocr_correct: bool = False) -> MrzResult:
    """Parse TD1 format (3 x 30, ID cards)."""
    m1 = _TD1_LINE1.match(text)
    if not m1:
        raise MrzParseError("TD1: cannot parse line 1")
    doc_code = m1.group(1)
    issuing_state = m1.group(2)
    doc_number = m1.group(3)
    doc_check = m1.group(4)
    optional1 = m1.group(5)

    m2 = _TD1_LINE2.match(text, 30)
    if not m2:
        raise MrzParseError("TD1: cannot parse line 2")
    dob_raw = m2.group(1)
    dob_check = m2.group(2)
    sex_raw = m2.group(3)
    expiry_raw = m2.group(4)
    expiry_check = m2.group(5)
    nationality = m2.group(6)
    optional2 = m2.group(7)
    overall_check = m2.group(8)

    m3 = _TD1_LINE3.match(text, 60)
    if not m3:
        raise MrzParseError("TD1: cannot parse line 3")
    surname, given_names = split_names(m3.group(1))

    if ocr_correct:
        dob_raw = ocr.correct_date(dob_raw)
        dob_check = ocr.correct_date(dob_check)
        expiry_raw = ocr.correct_date(expiry_raw)
        expiry_check = ocr.correct_date(expiry_check)
        nationality = ocr.correct_alpha(nationality)
        issuing_state = ocr.correct_alpha(issuing_state)
        sex_raw = ocr.correct_sex(sex_raw)

    valid = (
        checksum.verify_extended(doc_number, doc_check, optional1)
        and checksum.verify(dob_raw, dob_check)
        and checksum.verify(expiry_raw, expiry_check)
        and checksum.verify(
            doc_number + doc_check + optional1
            + dob_raw + dob_check
            + expiry_raw + expiry_check
            + optional2,
            overall_check,
        )
    )

    return MrzResult(
        format=MrzFormat.TD1,
        document_type=doc_code[0],
        document_type_additional=doc_code[1] if len(doc_code) > 1 else "",
        issuing_country=unpad(issuing_state),
        surname=surname,
        given_names=given_names,
        document_number=unpad(doc_number),
        nationality=unpad(nationality),
        date_of_birth=dob_raw,
        sex=Sex.from_mrz(sex_raw),
        expiry_date=expiry_raw,
        birth_date=parse_mrz_date(dob_raw, is_birth=True),
        expiry_date_parsed=parse_mrz_date(expiry_raw, is_birth=False),
        optional_data_1=unpad(optional1),
        optional_data_2=unpad(optional2),
        check_digits_valid=valid,
        raw_mrz=text,
    )


# ── TD2: 2 x 36 ────────────────────────────────────────

_TD2_LINE1 = re.compile(
    r"([A-UW-Z]{1}[A-Z0-9<]{1})"
    r"([A-Z<]{3})"
    r"([A-Z<]{31})"
)

_TD2_LINE2 = re.compile(
    r"([A-Z0-9<]{9})"
    r"([0-9<]{1})"
    r"([A-Z<]{3})"
    r"([0-9<]{6})"
    r"([0-9<]{1})"
    r"([MFX<]{1})"
    r"([0-9<]{6})"
    r"([0-9<]{1})"
    r"([A-Z0-9<]{7})"
    r"([0-9<]{1})"
)


def parse_td2(text: str, *, ocr_correct: bool = False) -> MrzResult:
    """Parse TD2 format (2 x 36, travel documents)."""
    m1 = _TD2_LINE1.match(text)
    if not m1:
        raise MrzParseError("TD2: cannot parse line 1")
    doc_code = m1.group(1)
    issuing_state = m1.group(2)
    surname, given_names = split_names(m1.group(3))

    m2 = _TD2_LINE2.match(text, 36)
    if not m2:
        raise MrzParseError("TD2: cannot parse line 2")
    doc_number = m2.group(1)
    doc_check = m2.group(2)
    nationality = m2.group(3)
    dob_raw = m2.group(4)
    dob_check = m2.group(5)
    sex_raw = m2.group(6)
    expiry_raw = m2.group(7)
    expiry_check = m2.group(8)
    optional = m2.group(9)
    overall_check = m2.group(10)

    if ocr_correct:
        dob_raw = ocr.correct_date(dob_raw)
        dob_check = ocr.correct_date(dob_check)
        expiry_raw = ocr.correct_date(expiry_raw)
        expiry_check = ocr.correct_date(expiry_check)
        nationality = ocr.correct_alpha(nationality)
        issuing_state = ocr.correct_alpha(issuing_state)
        sex_raw = ocr.correct_sex(sex_raw)

    valid = (
        checksum.verify_extended(doc_number, doc_check, optional)
        and checksum.verify(dob_raw, dob_check)
        and checksum.verify(expiry_raw, expiry_check)
        and checksum.verify(
            doc_number + doc_check
            + dob_raw + dob_check
            + expiry_raw + expiry_check
            + optional,
            overall_check,
        )
    )

    return MrzResult(
        format=MrzFormat.TD2,
        document_type=doc_code[0],
        document_type_additional=doc_code[1] if len(doc_code) > 1 else "",
        issuing_country=unpad(issuing_state),
        surname=surname,
        given_names=given_names,
        document_number=unpad(doc_number),
        nationality=unpad(nationality),
        date_of_birth=dob_raw,
        sex=Sex.from_mrz(sex_raw),
        expiry_date=expiry_raw,
        birth_date=parse_mrz_date(dob_raw, is_birth=True),
        expiry_date_parsed=parse_mrz_date(expiry_raw, is_birth=False),
        optional_data_1=unpad(optional),
        check_digits_valid=valid,
        raw_mrz=text,
    )


# ── TD3: 2 x 44 ────────────────────────────────────────

_TD3_LINE1 = re.compile(
    r"([A-UW-Z]{1}[A-Z0-9<]{1})"
    r"([A-Z<]{3})"
    r"([A-Z<]{39})"
)

_TD3_LINE2 = re.compile(
    r"([A-Z0-9<]{9})"
    r"([0-9<]{1})"
    r"([A-Z<]{3})"
    r"([0-9<]{6})"
    r"([0-9<]{1})"
    r"([MFX<]{1})"
    r"([0-9<]{6})"
    r"([0-9<]{1})"
    r"([A-Z0-9<]{14})"
    r"([0-9<]{1})"
    r"([0-9<]{1})"
)


def parse_td3(text: str, *, ocr_correct: bool = False) -> MrzResult:
    """Parse TD3 format (2 x 44, passports)."""
    m1 = _TD3_LINE1.match(text)
    if not m1:
        raise MrzParseError("TD3: cannot parse line 1")
    doc_code = m1.group(1)
    issuing_state = m1.group(2)
    surname, given_names = split_names(m1.group(3))

    m2 = _TD3_LINE2.match(text, 44)
    if not m2:
        raise MrzParseError("TD3: cannot parse line 2")
    doc_number = m2.group(1)
    doc_check = m2.group(2)
    nationality = m2.group(3)
    dob_raw = m2.group(4)
    dob_check = m2.group(5)
    sex_raw = m2.group(6)
    expiry_raw = m2.group(7)
    expiry_check = m2.group(8)
    personal_num = m2.group(9)
    personal_check = m2.group(10)
    overall_check = m2.group(11)

    if ocr_correct:
        dob_raw = ocr.correct_date(dob_raw)
        dob_check = ocr.correct_date(dob_check)
        expiry_raw = ocr.correct_date(expiry_raw)
        expiry_check = ocr.correct_date(expiry_check)
        nationality = ocr.correct_alpha(nationality)
        issuing_state = ocr.correct_alpha(issuing_state)
        sex_raw = ocr.correct_sex(sex_raw)

    valid = (
        checksum.verify(doc_number, doc_check)
        and checksum.verify(dob_raw, dob_check)
        and checksum.verify(expiry_raw, expiry_check)
        and checksum.verify(personal_num, personal_check)
        and checksum.verify(
            doc_number + doc_check
            + dob_raw + dob_check
            + expiry_raw + expiry_check
            + personal_num + personal_check,
            overall_check,
        )
    )

    return MrzResult(
        format=MrzFormat.TD3,
        document_type=doc_code[0],
        document_type_additional=doc_code[1] if len(doc_code) > 1 else "",
        issuing_country=unpad(issuing_state),
        surname=surname,
        given_names=given_names,
        document_number=unpad(doc_number),
        nationality=unpad(nationality),
        date_of_birth=dob_raw,
        sex=Sex.from_mrz(sex_raw),
        expiry_date=expiry_raw,
        birth_date=parse_mrz_date(dob_raw, is_birth=True),
        expiry_date_parsed=parse_mrz_date(expiry_raw, is_birth=False),
        personal_number=unpad(personal_num),
        check_digits_valid=valid,
        raw_mrz=text,
    )


# ── Public API ──────────────────────────────────────────


def parse_mrz(
    text: str,
    *,
    ocr_correct: bool = False,
    auto_purify: bool = False,
    canada_only: bool = True,
) -> MrzResult:
    """Parse an MRZ string and return a structured MrzResult.

    Args:
        text: Raw MRZ string (can contain newlines).
        ocr_correct: Apply OCR error correction before parsing.
        auto_purify: Strip invalid characters before parsing.
        canada_only: Reject non-Canadian documents.

    Raises:
        MrzParseError: When the text cannot be parsed.
        ValueError: When canada_only=True and document is not CAN.
    """
    from canada_id.mrz.utils import purify as _purify

    # Try extracting valid MRZ lines from raw text first
    # (before stripping newlines which destroys line boundaries)
    raw_for_extract = text.replace("\r", "")
    text = raw_for_extract.replace(" ", "")
    if "\n" in text:
        text = "".join(
            line.strip() for line in text.split("\n") if line.strip()
        )
    if auto_purify:
        text = _purify(text)

    # OCR filler correction: letters commonly misread for <
    if ocr_correct:
        text = _fix_ocr_fillers(text)

    # If length doesn't match any format, try extracting
    # valid MRZ lines from the raw text (preserves line breaks)
    if len(text) not in (90, 72, 88):
        extracted = _extract_mrz_lines(raw_for_extract)
        if extracted:
            text = extracted

    # Off-by-one fix: trim trailing < if 1 char over
    if len(text) in (91, 73, 89):
        if text[-1] == "<":
            text = text[:-1]

    fmt = detect_format(text)

    if fmt == MrzFormat.TD1:
        result = parse_td1(text, ocr_correct=ocr_correct)
    elif fmt == MrzFormat.TD2:
        result = parse_td2(text, ocr_correct=ocr_correct)
    elif fmt == MrzFormat.TD3:
        result = parse_td3(text, ocr_correct=ocr_correct)
    else:
        raise MrzParseError(f"Unsupported format: {fmt}")

    if canada_only and not result.is_canadian:
        raise ValueError(
            f"Not a Canadian document (issuing country:"
            f" {result.issuing_country}). Set canada_only=False"
            f" to parse non-Canadian MRZ."
        )

    return result


def validate_mrz(
    text: str,
    *,
    ocr_correct: bool = False,
    canada_only: bool = True,
) -> bool:
    """Return True if all check digits pass."""
    try:
        result = parse_mrz(
            text, ocr_correct=ocr_correct, canada_only=canada_only,
        )
        return result.check_digits_valid
    except (MrzParseError, ValueError):
        return False
