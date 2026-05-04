"""Canadian document type definitions for MRZ generation.

Covers all Canadian MRZ-bearing documents per ICAO 9303 and IRCC specs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanadianDocType:
    """Definition of a Canadian MRZ document type.

    Attributes (educational metadata):
        card_eras: Historical card versions in circulation.
        chip_type: Embedded chip technology, if any.
        has_pdf417: Whether the card has a PDF417 barcode.
        doc_number_formats: Accepted document number patterns.
    """

    key: str
    name: str
    mrz_format: str
    document_type: str
    issuing_country: str
    description: str
    optional_data_1_label: str = "Optional Data 1"
    optional_data_2_label: str = "Optional Data 2"
    nationality_note: str = ""
    sample_surname: str = "SMITH"
    sample_given: str = "JOHN"
    sample_doc_num: str = "AB1234567"
    sample_nationality: str = "CAN"
    sample_dob: str = "900115"
    sample_sex: str = "M"
    sample_expiry: str = "340115"
    sample_opt1: str = ""
    sample_opt2: str = ""
    # Educational metadata (per ICAO/IRCC public spec)
    card_eras: tuple = ()
    chip_type: str = ""
    has_pdf417: bool = False
    doc_number_formats: tuple = ()


CANADIAN_DOCS: dict[str, CanadianDocType] = {}


def _reg(doc: CanadianDocType) -> None:
    """Register a document type."""
    CANADIAN_DOCS[doc.key] = doc


_reg(CanadianDocType(
    key="passport",
    name="Passport",
    mrz_format="TD3",
    document_type="P",
    issuing_country="CAN",
    description=(
        "Canadian passport (TD3, 2x44). Standard passport"
        " issued by IRCC. Supports M/F/X gender."
        " ePassport chip embedded since 1 July 2013."
    ),
    optional_data_1_label="Personal Number (14 chars max)",
    nationality_note="Always CAN for citizens",
    sample_surname="TREMBLAY",
    sample_given="MARIE CLAIRE",
    sample_doc_num="AB1234567",
    sample_nationality="CAN",
    sample_dob="850320",
    sample_sex="F",
    sample_expiry="340320",
    card_eras=(
        ("Pre-May 2023", "Doc# format: AB123456 (8 chars: 2 letters + 6 digits)"),
        ("Post-May 2023", "Doc# format: A123456BC (9 chars: 1 letter + 6 digits + 2 letters)"),
    ),
    chip_type="ePassport (ISO 14443B, BAC, ICAO LDS) - since 2013-07-01",
    has_pdf417=False,
    doc_number_formats=(
        r"^[A-Z]{2}\d{6}$",       # legacy
        r"^[A-Z]\d{6}[A-Z]{2}$",  # current
    ),
))

_reg(CanadianDocType(
    key="pr_card",
    name="Permanent Resident Card",
    mrz_format="TD1",
    document_type="CA",
    issuing_country="CAN",
    description=(
        "Canadian PR Card (TD1, 3x30). Issued by IRCC."
        " Doc type code is 'CA' (Canada-specific), NOT 'I<'."
        " Nationality may differ from issuing country"
        " (holder keeps their original nationality)."
        " Three card eras with different security features."
    ),
    optional_data_1_label=(
        "UCI / Client ID with structure: <DDDDDDDDDD<<<X"
        " (15 chars: < + 10-digit UCI + 3 fillers + 1 check)"
    ),
    optional_data_2_label=(
        "Issue date + sequence: <YYMMDD<NN< (11 chars)"
    ),
    nationality_note=(
        "Holder's actual nationality, NOT CAN."
        " E.g. BGD, CMR, IND, CHN, PHL."
    ),
    sample_surname="MAGHA MOFFO",
    sample_given="MATHILDE",
    sample_doc_num="PD0183017",
    sample_nationality="CMR",
    sample_dob="841127",
    sample_sex="F",
    sample_expiry="260430",
    sample_opt1="<1110153398<<<5",  # real format: <UCI<<<X
    sample_opt2="<210430<01<",       # real format: <YYMMDD<NN<
    card_eras=(
        ("2002-2009", "Original. PDF417 barcode on back."),
        ("2009-2014", "Redesigned. Optical stripe + PDF417 barcode."),
        ("2015-present", "RFID chip (CBSA-only opaque ID). PDF417 REMOVED."),
    ),
    chip_type=(
        "RFID (ISO 14443, opaque ID only) - 2015+ cards. "
        "Read by CBSA at land borders only. NOT an ICAO ePassport chip."
    ),
    has_pdf417=False,  # post-2015 cards (current default)
    doc_number_formats=(
        r"^[A-Z]{2}\d{7}$",  # 2 letters + 7 digits
    ),
))

_reg(CanadianDocType(
    key="edl",
    name="Enhanced Driver's License",
    mrz_format="TD1",
    document_type="I",
    issuing_country="CAN",
    description=(
        "Enhanced Driver's License (TD1, 3x30)."
        " WHTI-compliant for land/sea US entry."
        " Issued by BC, MB, ON (discontinued), QC."
    ),
    optional_data_1_label="DL Number / Province Code",
    optional_data_2_label="Optional Data 2",
    nationality_note="Always CAN",
    sample_surname="SINGH",
    sample_given="HARPREET",
    sample_doc_num="D12345678",
    sample_nationality="CAN",
    sample_dob="880515",
    sample_sex="M",
    sample_expiry="290515",
    sample_opt1="BC",
))

_reg(CanadianDocType(
    key="nexus",
    name="NEXUS Card",
    mrz_format="TD1",
    document_type="I",
    issuing_country="CAN",
    description=(
        "NEXUS trusted traveler card (TD1, 3x30)."
        " Joint CBSA/CBP program. Valid for"
        " US-Canada land, sea, and designated air."
    ),
    optional_data_1_label="NEXUS Membership Number",
    optional_data_2_label="Optional Data 2",
    nationality_note="CAN for Canadian-issued",
    sample_surname="CHEN",
    sample_given="WEI",
    sample_doc_num="N98765432",
    sample_nationality="CAN",
    sample_dob="750810",
    sample_sex="F",
    sample_expiry="300810",
))

_reg(CanadianDocType(
    key="refugee_travel",
    name="Refugee Travel Document",
    mrz_format="TD3",
    document_type="P",
    issuing_country="CAN",
    description=(
        "Convention Travel Document (TD3, 2x44)."
        " Issued to refugees and protected persons."
        " Looks like passport but blue cover."
    ),
    optional_data_1_label="IRCC File Number",
    nationality_note=(
        "Holder's actual nationality or XXX"
        " (stateless/unspecified)"
    ),
    sample_surname="AHMED",
    sample_given="FATIMA",
    sample_doc_num="RT1234567",
    sample_nationality="XXX",
    sample_dob="950101",
    sample_sex="F",
    sample_expiry="300101",
))

_reg(CanadianDocType(
    key="emergency_travel",
    name="Emergency Travel Document",
    mrz_format="TD3",
    document_type="P",
    issuing_country="CAN",
    description=(
        "Emergency Travel Document (TD3, 2x44)."
        " Single-journey, issued by consulates"
        " when passport is lost abroad."
        " Very short expiry (days/weeks)."
    ),
    optional_data_1_label="Mission Identifier",
    nationality_note="Always CAN",
    sample_surname="WILLIAMS",
    sample_given="JAMES",
    sample_doc_num="EM0001234",
    sample_nationality="CAN",
    sample_dob="800601",
    sample_sex="M",
    sample_expiry="240501",
))


def get_doc_type(key: str) -> CanadianDocType:
    """Get a Canadian document type by key.

    Raises:
        KeyError: If key not found.
    """
    return CANADIAN_DOCS[key]


def all_doc_types() -> list[CanadianDocType]:
    """Return all Canadian document types."""
    return list(CANADIAN_DOCS.values())


def doc_choices() -> list[str]:
    """Return dropdown choices for the UI."""
    return [f"{d.key} - {d.name}" for d in all_doc_types()]
