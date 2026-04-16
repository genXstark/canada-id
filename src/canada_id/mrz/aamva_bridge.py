"""Bridge to convert AAMVA field data to MRZ format."""

from __future__ import annotations

from canada_id.mrz.generator import MRZData

SEX_MAP = {"1": "M", "2": "F", "9": "X"}


def aamva_to_mrz_data(
    fields: dict[str, str],
    document_type: str = "I",
    document_number: str | None = None,
) -> MRZData:
    """Convert AAMVA field dict to MRZData for MRZ generation.

    Args:
        fields: AAMVA field dict (from parse_aamva or user input).
        document_type: MRZ document type (I=ID, P=passport).
        document_number: Override document number. Defaults to DAQ.

    Returns:
        MRZData populated from AAMVA fields.
    """
    sex_code = fields.get("DBC", "9")
    sex = SEX_MAP.get(sex_code, "X")

    dob = fields.get("DBB", "")
    expiry = fields.get("DBA", "")

    doc_num = document_number or fields.get("DAQ", "")
    doc_num = doc_num.replace("-", "").replace(" ", "")[:9]

    surname = fields.get("DCS", "")
    given = fields.get("DAC", "")
    middle = fields.get("DAD", "")
    if middle:
        given = f"{given} {middle}"

    country = "CAN" if fields.get("DCG", "CAN") == "CAN" else "USA"
    province = fields.get("DAJ", "")

    return MRZData(
        document_type=document_type,
        country_code=country,
        surname=surname,
        given_names=given,
        document_number=doc_num,
        nationality=country,
        date_of_birth=dob,
        sex=sex,
        expiry_date=expiry,
        optional_data_1=province,
        optional_data_2="",
    )
