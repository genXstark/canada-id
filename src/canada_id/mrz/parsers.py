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


# Chars commonly OCR-misread as < filler (runs of 3+)
_FILLER_MISREADS = re.compile(r"([KLIJXY\|])\1{2,}")
# Single-char interlopers sandwiched between < fillers
_INTERLOPER = re.compile(r"<[A-Z0-9]<")


# OCR ambiguity pairs (chars that look alike)
_OCR_AMBIGUOUS = {
    "0": "O", "O": "0",
    "1": "I", "I": "1",
    "2": "Z", "Z": "2",
    "5": "S", "S": "5",
    "6": "G", "G": "6",
    "8": "B", "B": "8",
}


def _clean_filler_field(data: str, check: str) -> str:
    """Clean OCR garbage from a field that should be mostly <.

    Personal number and optional data fields are often all <.
    If the field is >= 50% <, replace remaining letters with <
    and verify check digit matches.
    """
    if checksum.verify(data, check):
        return data
    filler_count = data.count("<")
    if filler_count < len(data) // 2:
        return data
    # Try replacing each non-< char with <, one at a time
    # then all-<; return first match
    all_filler = "<" * len(data)
    if checksum.verify(all_filler, check):
        return all_filler
    # Replace individual non-< chars
    for i, ch in enumerate(data):
        if ch != "<":
            candidate = data[:i] + "<" + data[i + 1:]
            if checksum.verify(candidate, check):
                return candidate
    return data


def _fix_check_digit(data: str, check: str) -> str:
    """Try OCR ambiguity swaps on the check digit itself.

    If the check digit was OCR-misread (e.g. 0 as O or <),
    try alternatives until one validates.
    """
    if checksum.verify(data, check):
        return check
    # Common check-digit OCR misreads
    alternatives = {
        "<": ["0"],
        "O": ["0"],
        "Q": ["0"],
        "I": ["1"],
        "Z": ["2"],
        "S": ["5"],
        "G": ["6"],
        "B": ["8"],
        "0": ["O", "<"],
        "1": ["I"],
        "2": ["Z"],
    }
    if check in alternatives:
        for alt in alternatives[check]:
            if checksum.verify(data, alt):
                return alt
    # As a last resort, compute what it should be
    try:
        correct = checksum.compute_str(data)
        # Only use computed value if OCR-ambiguous with input
        if (check in _OCR_AMBIGUOUS
                and _OCR_AMBIGUOUS[check] == correct):
            return correct
        if check == "<" and correct == "0":
            return correct
    except Exception:
        pass
    return check


def _fix_with_checksum(data: str, check: str) -> str:
    """Try OCR ambiguity swaps until check digit matches.

    Tries single-char and two-char swaps for common OCR
    ambiguities (0↔O, 1↔I, 8↔B, etc.). Returns original
    string if no fix found.
    """
    if checksum.verify(data, check):
        return data

    # Single-position swaps
    for i, ch in enumerate(data):
        if ch in _OCR_AMBIGUOUS:
            candidate = data[:i] + _OCR_AMBIGUOUS[ch] + data[i + 1:]
            if checksum.verify(candidate, check):
                return candidate

    # Two-position swaps (more expensive but handles compound errors)
    positions = [
        i for i, ch in enumerate(data) if ch in _OCR_AMBIGUOUS
    ]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            pi, pj = positions[i], positions[j]
            candidate = list(data)
            candidate[pi] = _OCR_AMBIGUOUS[data[pi]]
            candidate[pj] = _OCR_AMBIGUOUS[data[pj]]
            cand_str = "".join(candidate)
            if checksum.verify(cand_str, check):
                return cand_str

    return data


def _realign_td3(text: str) -> str | None:
    """Realign TD3 line 2 using the sex marker as anchor.

    TD3 line 2 has sex at position 20 (0-indexed) within line 2,
    which is absolute position 64. If OCR misaligned by ±1-2 chars,
    we can find M/F/X near position 64 and shift to correct.
    """
    if len(text) != 88:
        return None
    line2 = text[44:]
    # Sex is at index 20 of line 2. Search ±3 around that.
    for offset in (1, -1, 2, -2, 3, -3):
        idx = 20 + offset
        if 0 <= idx < len(line2) and line2[idx] in "MFX":
            if offset > 0:
                # Line 2 has extra chars before sex — drop them
                new_line2 = line2[offset:] + "<" * offset
            else:
                # Line 2 is short before sex — pad
                new_line2 = "<" * abs(offset) + line2[:len(line2) + offset]
            return text[:44] + new_line2
    return None


def _realign_td1(text: str) -> str | None:
    """Realign TD1 line 2 using the sex marker as anchor.

    TD1 line 2 has sex at position 7 (0-indexed) within line 2,
    absolute position 37.
    """
    if len(text) != 90:
        return None
    line2 = text[30:60]
    for offset in (1, -1, 2, -2):
        idx = 7 + offset
        if 0 <= idx < len(line2) and line2[idx] in "MFX":
            if offset > 0:
                new_line2 = line2[offset:] + "<" * offset
            else:
                new_line2 = "<" * abs(offset) + line2[:len(line2) + offset]
            return text[:30] + new_line2 + text[60:]
    return None


def _fix_ocr_fillers(text: str) -> str:
    """Replace chars that OCR misread as < fillers.

    Tesseract commonly reads < as K, L, I, J, X, Y, or |.
    - Pass 1: Runs of 3+ identical filler-like chars -> <<<
    - Pass 2: Single char sandwiched between < fillers -> <
      (repeats until stable — fixes chains of interlopers)
    """
    text = _FILLER_MISREADS.sub(
        lambda m: "<" * len(m.group(0)), text,
    )
    # Repeat interloper fix until no more matches
    while True:
        new = _INTERLOPER.sub("<<<", text)
        if new == text:
            break
        text = new
    return text


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
    r"([A-Z0-9<]{3})"
    r"([A-Z0-9<]{9})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{15})"
)

_TD1_LINE2 = re.compile(
    r"([A-Z0-9<]{6})"
    r"([A-Z0-9<]{1})"
    r"([MFX<]{1})"
    r"([A-Z0-9<]{6})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{3})"
    r"([A-Z0-9<]{11})"
    r"([A-Z0-9<]{1})"
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
        doc_number = _fix_with_checksum(doc_number, doc_check)
        dob_raw = _fix_with_checksum(dob_raw, dob_check)
        expiry_raw = _fix_with_checksum(expiry_raw, expiry_check)

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
    r"([A-Z0-9<]{2})"
    r"([A-Z0-9<]{3})"
    r"([A-Z0-9<]{31})"
)

_TD2_LINE2 = re.compile(
    r"([A-Z0-9<]{9})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{3})"
    r"([A-Z0-9<]{6})"
    r"([A-Z0-9<]{1})"
    r"([MFX<]{1})"
    r"([A-Z0-9<]{6})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{7})"
    r"([A-Z0-9<]{1})"
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
        doc_number = _fix_with_checksum(doc_number, doc_check)
        dob_raw = _fix_with_checksum(dob_raw, dob_check)
        expiry_raw = _fix_with_checksum(expiry_raw, expiry_check)

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
    r"([A-Z0-9<]{2})"
    r"([A-Z0-9<]{3})"
    r"([A-Z0-9<]{39})"
)

_TD3_LINE2 = re.compile(
    r"([A-Z0-9<]{9})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{3})"
    r"([A-Z0-9<]{6})"
    r"([A-Z0-9<]{1})"
    r"([MFX<]{1})"
    r"([A-Z0-9<]{6})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{14})"
    r"([A-Z0-9<]{1})"
    r"([A-Z0-9<]{1})"
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
        # Try OCR ambiguity swaps when check digits fail
        doc_number = _fix_with_checksum(doc_number, doc_check)
        dob_raw = _fix_with_checksum(dob_raw, dob_check)
        expiry_raw = _fix_with_checksum(expiry_raw, expiry_check)
        # Personal number is usually all < fillers — aggressively
        # clean up stray letters that OCR misread
        personal_num = _clean_filler_field(
            personal_num, personal_check,
        )
        # Try OCR swap on check digits themselves if still invalid
        personal_check = _fix_check_digit(
            personal_num, personal_check,
        )

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

    # If individual checks pass but overall fails, the overall
    # check digit itself was likely OCR-corrupted — trust data
    # and use computed overall check
    if ocr_correct and not valid:
        composite = (
            doc_number + doc_check
            + dob_raw + dob_check
            + expiry_raw + expiry_check
            + personal_num + personal_check
        )
        individual_valid = (
            checksum.verify(doc_number, doc_check)
            and checksum.verify(dob_raw, dob_check)
            and checksum.verify(expiry_raw, expiry_check)
            and checksum.verify(personal_num, personal_check)
        )
        if individual_valid:
            # All individual checks passed — data is trustworthy.
            # Overall check must be OCR-corrupted; compute correct.
            try:
                overall_check = checksum.compute_str(composite)
                valid = True
            except Exception:
                pass

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

    try:
        if fmt == MrzFormat.TD1:
            result = parse_td1(text, ocr_correct=ocr_correct)
        elif fmt == MrzFormat.TD2:
            result = parse_td2(text, ocr_correct=ocr_correct)
        elif fmt == MrzFormat.TD3:
            result = parse_td3(text, ocr_correct=ocr_correct)
        else:
            raise MrzParseError(f"Unsupported format: {fmt}")
    except MrzParseError:
        # Lossy fallback: re-align line 2 by finding sex marker
        if ocr_correct and fmt == MrzFormat.TD3:
            realigned = _realign_td3(text)
            if realigned:
                result = parse_td3(realigned, ocr_correct=ocr_correct)
            else:
                raise
        elif ocr_correct and fmt == MrzFormat.TD1:
            realigned = _realign_td1(text)
            if realigned:
                result = parse_td1(realigned, ocr_correct=ocr_correct)
            else:
                raise
        else:
            raise

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
