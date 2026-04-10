"""MRZ generator for Canadian identity documents (ICAO 9303).

Supports TD1 (3-line, 30 chars/line) for ID cards,
TD2 (2-line, 36 chars/line) for travel documents,
and TD3 (2-line, 44 chars/line) for passports.
"""
from __future__ import annotations

from dataclasses import dataclass

from canada_id.mrz.checkdigit import compute_check_digit


def _pad(value: str, length: int) -> str:
    """Pad or truncate a value to exact length with '<' filler."""
    cleaned = value.upper().replace(" ", "<")
    if len(cleaned) > length:
        return cleaned[:length]
    return cleaned.ljust(length, "<")


def _format_name(surname: str, given_names: str, length: int) -> str:
    """Format name field: SURNAME<<GIVEN<NAMES, padded to length."""
    surname_clean = surname.upper().replace(" ", "<").replace(",", "<")
    given_clean = given_names.upper().replace(" ", "<").replace(",", "<")
    combined = f"{surname_clean}<<{given_clean}"
    return _pad(combined, length)


def _format_date(date_str: str) -> str:
    """Convert date from CCYYMMDD or YYMMDD to YYMMDD for MRZ."""
    digits = date_str.replace("-", "").replace("/", "")
    if len(digits) == 8:
        return digits[2:]
    if len(digits) == 6:
        return digits
    raise ValueError(f"Invalid date format: {date_str!r}")


@dataclass
class MRZData:
    """Input data for MRZ generation.

    Attributes:
        document_type: 1-2 char doc type (I=ID, P=passport, etc.)
        country_code: 3-letter issuing country (CAN for Canada).
        surname: Family name.
        given_names: Given name(s), space-separated.
        document_number: Document/passport number.
        nationality: 3-letter nationality code.
        date_of_birth: CCYYMMDD or YYMMDD format.
        sex: M, F, or X (non-specified).
        expiry_date: CCYYMMDD or YYMMDD format.
        optional_data_1: Optional data line 1 (TD1 only).
        optional_data_2: Optional data line 2 (TD1/TD2).
    """

    document_type: str = "I"
    country_code: str = "CAN"
    surname: str = ""
    given_names: str = ""
    document_number: str = ""
    nationality: str = "CAN"
    date_of_birth: str = ""
    sex: str = "M"
    expiry_date: str = ""
    optional_data_1: str = ""
    optional_data_2: str = ""


def generate_td1(data: MRZData) -> str:
    """Generate TD1 MRZ (3 lines x 30 chars) for ID cards.

    Returns:
        3-line MRZ string separated by newlines.
    """
    doc_type = _pad(data.document_type, 2)
    country = _pad(data.country_code, 3)
    doc_num = _pad(data.document_number, 9)
    doc_num_cd = compute_check_digit(doc_num)
    opt1 = _pad(data.optional_data_1, 15)

    line1 = f"{doc_type}{country}{doc_num}{doc_num_cd}{opt1}"
    assert len(line1) == 30, f"Line 1 length: {len(line1)}"

    dob = _format_date(data.date_of_birth)
    dob_cd = compute_check_digit(dob)
    sex = data.sex.upper()[0] if data.sex else "<"
    exp = _format_date(data.expiry_date)
    exp_cd = compute_check_digit(exp)
    nationality = _pad(data.nationality, 3)
    opt2 = _pad(data.optional_data_2, 11)

    composite = doc_num + doc_num_cd + opt1 + dob + dob_cd + exp + exp_cd + opt2
    overall_cd = compute_check_digit(composite)

    line2 = f"{dob}{dob_cd}{sex}{exp}{exp_cd}{nationality}{opt2}{overall_cd}"
    assert len(line2) == 30, f"Line 2 length: {len(line2)}"

    line3 = _format_name(data.surname, data.given_names, 30)

    return f"{line1}\n{line2}\n{line3}"


def generate_td2(data: MRZData) -> str:
    """Generate TD2 MRZ (2 lines x 36 chars) for travel documents.

    Returns:
        2-line MRZ string separated by newline.
    """
    doc_type = _pad(data.document_type, 2)
    country = _pad(data.country_code, 3)
    name = _format_name(data.surname, data.given_names, 31)

    line1 = f"{doc_type}{country}{name}"
    assert len(line1) == 36, f"Line 1 length: {len(line1)}"

    doc_num = _pad(data.document_number, 9)
    doc_num_cd = compute_check_digit(doc_num)
    nationality = _pad(data.nationality, 3)
    dob = _format_date(data.date_of_birth)
    dob_cd = compute_check_digit(dob)
    sex = data.sex.upper()[0] if data.sex else "<"
    exp = _format_date(data.expiry_date)
    exp_cd = compute_check_digit(exp)
    opt = _pad(data.optional_data_1, 7)

    composite = doc_num + doc_num_cd + dob + dob_cd + exp + exp_cd + opt
    overall_cd = compute_check_digit(composite)

    line2 = (
        f"{doc_num}{doc_num_cd}{nationality}{dob}{dob_cd}"
        f"{sex}{exp}{exp_cd}{opt}{overall_cd}"
    )
    assert len(line2) == 36, f"Line 2 length: {len(line2)}"

    return f"{line1}\n{line2}"


def generate_td3(data: MRZData) -> str:
    """Generate TD3 MRZ (2 lines x 44 chars) for passports.

    Returns:
        2-line MRZ string separated by newline.
    """
    doc_type = _pad(data.document_type or "P", 2)
    country = _pad(data.country_code, 3)
    name = _format_name(data.surname, data.given_names, 39)

    line1 = f"{doc_type}{country}{name}"
    assert len(line1) == 44, f"Line 1 length: {len(line1)}"

    doc_num = _pad(data.document_number, 9)
    doc_num_cd = compute_check_digit(doc_num)
    nationality = _pad(data.nationality, 3)
    dob = _format_date(data.date_of_birth)
    dob_cd = compute_check_digit(dob)
    sex = data.sex.upper()[0] if data.sex else "<"
    exp = _format_date(data.expiry_date)
    exp_cd = compute_check_digit(exp)
    personal_num = _pad(data.optional_data_1, 14)
    personal_cd = compute_check_digit(personal_num)

    composite = (
        doc_num + doc_num_cd + dob + dob_cd + exp + exp_cd
        + personal_num + personal_cd
    )
    overall_cd = compute_check_digit(composite)

    line2 = (
        f"{doc_num}{doc_num_cd}{nationality}{dob}{dob_cd}"
        f"{sex}{exp}{exp_cd}{personal_num}{personal_cd}{overall_cd}"
    )
    assert len(line2) == 44, f"Line 2 length: {len(line2)}"

    return f"{line1}\n{line2}"


def generate_mrz(data: MRZData, format_type: str = "TD1") -> str:
    """Generate MRZ string in the specified format.

    Args:
        data: MRZ input data.
        format_type: "TD1", "TD2", or "TD3".

    Returns:
        Multi-line MRZ string.
    """
    generators = {"TD1": generate_td1, "TD2": generate_td2, "TD3": generate_td3}
    fmt = format_type.upper()
    if fmt not in generators:
        raise ValueError(f"Unknown format: {format_type!r}. Use TD1/TD2/TD3.")
    return generators[fmt](data)
