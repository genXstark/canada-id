"""MRZ parser — extract fields from MRZ strings."""
from __future__ import annotations

from dataclasses import dataclass

from canada_id.mrz.checkdigit import verify_check_digit


@dataclass
class MRZResult:
    """Parsed MRZ data with validation status."""

    format_type: str
    document_type: str
    country_code: str
    surname: str
    given_names: str
    document_number: str
    nationality: str
    date_of_birth: str
    sex: str
    expiry_date: str
    optional_data_1: str
    optional_data_2: str
    valid: bool
    errors: list[str]


def _strip_filler(value: str) -> str:
    """Remove trailing '<' filler characters."""
    return value.rstrip("<").replace("<", " ")


def _detect_format(lines: list[str]) -> str:
    """Detect MRZ format from line count and lengths."""
    if len(lines) == 3 and all(len(l) == 30 for l in lines):
        return "TD1"
    if len(lines) == 2 and all(len(l) == 36 for l in lines):
        return "TD2"
    if len(lines) == 2 and all(len(l) == 44 for l in lines):
        return "TD3"
    raise ValueError(
        f"Cannot detect MRZ format: {len(lines)} lines, "
        f"lengths {[len(l) for l in lines]}"
    )


def parse_td1(lines: list[str]) -> MRZResult:
    """Parse TD1 MRZ (3 lines x 30 chars)."""
    l1, l2, l3 = lines
    errors = []

    doc_type = l1[0:2].rstrip("<")
    country = l1[2:5]
    doc_num = l1[5:14]
    doc_num_cd = l1[14]
    opt1 = l1[15:30]

    if not verify_check_digit(doc_num, doc_num_cd):
        errors.append("Document number check digit invalid")

    dob = l2[0:6]
    dob_cd = l2[6]
    sex = l2[7]
    exp = l2[8:14]
    exp_cd = l2[14]
    nationality = l2[15:18]
    opt2 = l2[18:29]
    overall_cd = l2[29]

    if not verify_check_digit(dob, dob_cd):
        errors.append("Date of birth check digit invalid")
    if not verify_check_digit(exp, exp_cd):
        errors.append("Expiry date check digit invalid")

    composite = doc_num + doc_num_cd + opt1 + dob + dob_cd + exp + exp_cd + opt2
    if not verify_check_digit(composite, overall_cd):
        errors.append("Overall check digit invalid")

    name_parts = l3.split("<<", 1)
    surname = _strip_filler(name_parts[0])
    given = _strip_filler(name_parts[1]) if len(name_parts) > 1 else ""

    return MRZResult(
        format_type="TD1",
        document_type=doc_type,
        country_code=country,
        surname=surname,
        given_names=given,
        document_number=_strip_filler(doc_num),
        nationality=nationality,
        date_of_birth=dob,
        sex=sex,
        expiry_date=exp,
        optional_data_1=_strip_filler(opt1),
        optional_data_2=_strip_filler(opt2),
        valid=len(errors) == 0,
        errors=errors,
    )


def parse_td3(lines: list[str]) -> MRZResult:
    """Parse TD3 MRZ (2 lines x 44 chars)."""
    l1, l2 = lines
    errors = []

    doc_type = l1[0:2].rstrip("<")
    country = l1[2:5]
    name_field = l1[5:44]
    name_parts = name_field.split("<<", 1)
    surname = _strip_filler(name_parts[0])
    given = _strip_filler(name_parts[1]) if len(name_parts) > 1 else ""

    doc_num = l2[0:9]
    doc_num_cd = l2[9]
    nationality = l2[10:13]
    dob = l2[13:19]
    dob_cd = l2[19]
    sex = l2[20]
    exp = l2[21:27]
    exp_cd = l2[27]
    personal = l2[28:42]
    personal_cd = l2[42]
    overall_cd = l2[43]

    if not verify_check_digit(doc_num, doc_num_cd):
        errors.append("Document number check digit invalid")
    if not verify_check_digit(dob, dob_cd):
        errors.append("Date of birth check digit invalid")
    if not verify_check_digit(exp, exp_cd):
        errors.append("Expiry date check digit invalid")

    composite = (
        doc_num + doc_num_cd + dob + dob_cd
        + exp + exp_cd + personal + personal_cd
    )
    if not verify_check_digit(composite, overall_cd):
        errors.append("Overall check digit invalid")

    return MRZResult(
        format_type="TD3",
        document_type=doc_type,
        country_code=country,
        surname=surname,
        given_names=given,
        document_number=_strip_filler(doc_num),
        nationality=nationality,
        date_of_birth=dob,
        sex=sex,
        expiry_date=exp,
        optional_data_1=_strip_filler(personal),
        optional_data_2="",
        valid=len(errors) == 0,
        errors=errors,
    )


def parse_td2(lines: list[str]) -> MRZResult:
    """Parse TD2 MRZ (2 lines x 36 chars)."""
    l1, l2 = lines
    errors = []

    doc_type = l1[0:2].rstrip("<")
    country = l1[2:5]
    name_field = l1[5:36]
    name_parts = name_field.split("<<", 1)
    surname = _strip_filler(name_parts[0])
    given = _strip_filler(name_parts[1]) if len(name_parts) > 1 else ""

    doc_num = l2[0:9]
    doc_num_cd = l2[9]
    nationality = l2[10:13]
    dob = l2[13:19]
    dob_cd = l2[19]
    sex = l2[20]
    exp = l2[21:27]
    exp_cd = l2[27]
    opt = l2[28:35]
    overall_cd = l2[35]

    if not verify_check_digit(doc_num, doc_num_cd):
        errors.append("Document number check digit invalid")
    if not verify_check_digit(dob, dob_cd):
        errors.append("Date of birth check digit invalid")
    if not verify_check_digit(exp, exp_cd):
        errors.append("Expiry date check digit invalid")

    composite = doc_num + doc_num_cd + dob + dob_cd + exp + exp_cd + opt
    if not verify_check_digit(composite, overall_cd):
        errors.append("Overall check digit invalid")

    return MRZResult(
        format_type="TD2",
        document_type=doc_type,
        country_code=country,
        surname=surname,
        given_names=given,
        document_number=_strip_filler(doc_num),
        nationality=nationality,
        date_of_birth=dob,
        sex=sex,
        expiry_date=exp,
        optional_data_1=_strip_filler(opt),
        optional_data_2="",
        valid=len(errors) == 0,
        errors=errors,
    )


def parse_mrz(mrz_string: str) -> MRZResult:
    """Parse an MRZ string and return structured data.

    Args:
        mrz_string: Multi-line MRZ string.

    Returns:
        Parsed MRZ data with validation status.
    """
    lines = [l.strip() for l in mrz_string.strip().split("\n") if l.strip()]
    fmt = _detect_format(lines)
    parsers = {"TD1": parse_td1, "TD2": parse_td2, "TD3": parse_td3}
    return parsers[fmt](lines)
