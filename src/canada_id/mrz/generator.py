"""MRZ string generator for Canadian documents.

Generates valid MRZ strings with correct check digits for
TD1, TD2, and TD3 formats. Ported from MRZParser-develop.
"""
from __future__ import annotations

from dataclasses import dataclass

from canada_id.mrz.checksum import compute_str as _check
from canada_id.mrz.models import MrzFormat
from canada_id.mrz.utils import encode_name, pad


@dataclass
class MRZData:
    """Input data for MRZ generation.

    Attributes:
        document_type: 1-2 char doc type (I=ID, P=passport).
        country_code: 3-letter issuing country (CAN for Canada).
        surname: Family name.
        given_names: Given name(s), space-separated.
        document_number: Document/passport number.
        nationality: 3-letter nationality code.
        date_of_birth: YYMMDD format.
        sex: M, F, or X.
        expiry_date: YYMMDD format.
        optional_data_1: Optional data line 1.
        optional_data_2: Optional data line 2 (TD1 only).
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


def _format_date(date_str: str) -> str:
    """Convert CCYYMMDD or YYMMDD to YYMMDD for MRZ."""
    digits = date_str.replace("-", "").replace("/", "")
    if len(digits) == 8:
        return digits[2:]
    if len(digits) == 6:
        return digits
    return pad(digits, 6, "0")


def generate_mrz(
    data: MRZData,
    format_type: str | MrzFormat = "TD1",
) -> str:
    """Generate MRZ string in the specified format.

    Args:
        data: MRZ input data.
        format_type: "TD1", "TD2", "TD3" or MrzFormat enum.

    Returns:
        Continuous MRZ string (no newlines).
    """
    if isinstance(format_type, MrzFormat):
        fmt = format_type
    else:
        fmt = MrzFormat(format_type.upper())

    doc_type = pad(data.document_type.upper(), 2)
    country = pad(data.country_code.upper(), 3)
    nat = pad(data.nationality.upper(), 3)
    dob = _format_date(data.date_of_birth)
    sex = pad(data.sex.upper(), 1)
    exp = _format_date(data.expiry_date)
    doc_num = data.document_number.upper()

    if fmt == MrzFormat.TD1:
        return _generate_td1(
            doc_type, country, doc_num, nat,
            dob, sex, exp, data.surname, data.given_names,
            data.optional_data_1, data.optional_data_2,
        )
    if fmt == MrzFormat.TD2:
        return _generate_td2(
            doc_type, country, doc_num, nat,
            dob, sex, exp, data.surname, data.given_names,
            data.optional_data_1,
        )
    if fmt == MrzFormat.TD3:
        return _generate_td3(
            doc_type, country, doc_num, nat,
            dob, sex, exp, data.surname, data.given_names,
            data.optional_data_1,
        )
    raise ValueError(f"Unsupported format: {fmt}")


def _generate_td1(
    doc_type, country, doc_num, nationality,
    dob, sex, expiry, surname, given_names,
    opt1, opt2,
):
    """Generate TD1: 3 x 30."""
    doc_num_padded = pad(doc_num, 9)
    doc_check = _check(doc_num_padded)
    opt1_padded = pad(opt1, 15)

    line1 = doc_type + country + doc_num_padded + doc_check + opt1_padded

    dob_check = _check(dob)
    exp_check = _check(expiry)
    opt2_padded = pad(opt2, 11)

    composite = (
        doc_num_padded + doc_check + opt1_padded
        + dob + dob_check + expiry + exp_check + opt2_padded
    )
    overall_check = _check(composite)

    line2 = (
        dob + dob_check + sex + expiry + exp_check
        + nationality + opt2_padded + overall_check
    )

    line3 = encode_name(surname, given_names, 30)
    return line1 + line2 + line3


def _generate_td2(
    doc_type, country, doc_num, nationality,
    dob, sex, expiry, surname, given_names,
    opt,
):
    """Generate TD2: 2 x 36."""
    name_field = encode_name(surname, given_names, 31)
    line1 = doc_type + country + name_field

    doc_num_padded = pad(doc_num, 9)
    doc_check = _check(doc_num_padded)
    dob_check = _check(dob)
    exp_check = _check(expiry)
    opt_padded = pad(opt, 7)

    composite = (
        doc_num_padded + doc_check
        + dob + dob_check
        + expiry + exp_check
        + opt_padded
    )
    overall_check = _check(composite)

    line2 = (
        doc_num_padded + doc_check + nationality
        + dob + dob_check + sex + expiry + exp_check
        + opt_padded + overall_check
    )
    return line1 + line2


def _generate_td3(
    doc_type, country, doc_num, nationality,
    dob, sex, expiry, surname, given_names,
    personal_number,
):
    """Generate TD3: 2 x 44."""
    name_field = encode_name(surname, given_names, 39)
    line1 = doc_type + country + name_field

    doc_num_padded = pad(doc_num, 9)
    doc_check = _check(doc_num_padded)
    dob_check = _check(dob)
    exp_check = _check(expiry)
    pn_padded = pad(personal_number, 14)
    pn_check = _check(pn_padded)

    composite = (
        doc_num_padded + doc_check
        + dob + dob_check
        + expiry + exp_check
        + pn_padded + pn_check
    )
    overall_check = _check(composite)

    line2 = (
        doc_num_padded + doc_check + nationality
        + dob + dob_check + sex + expiry + exp_check
        + pn_padded + pn_check + overall_check
    )
    return line1 + line2
