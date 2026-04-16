"""AAMVA field definitions and registry.

Maps every standard AAMVA element ID to its definition including
name, card type, data type, max length, and required status.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDef:
    """Definition of a single AAMVA data element.

    Attributes:
        element_id: Three-character element identifier (e.g. "DAQ").
        name: Human-readable field name.
        card_type: "DL", "ID", or "Both".
        data_type: "ANS" (alphanumeric+special), "N" (numeric), "A" (alpha).
        max_length: Maximum character count.
        required: Whether the field is mandatory.
    """

    element_id: str
    name: str
    card_type: str
    data_type: str
    max_length: int
    required: bool


def _f(
    eid: str,
    name: str,
    card: str = "Both",
    dtype: str = "ANS",
    length: int = 40,
    req: bool = False,
) -> FieldDef:
    """Shorthand factory to reduce registry verbosity."""
    return FieldDef(eid, name, card, dtype, length, req)


FIELD_REGISTRY: dict[str, FieldDef] = {
    # --- Required identity fields ---
    "DCS": _f("DCS", "Customer Family Name", req=True),
    "DAC": _f("DAC", "Customer First Name", req=True),
    "DAD": _f("DAD", "Customer Middle Name(s)"),
    "DCU": _f("DCU", "Name Suffix", length=5),
    "DAQ": _f("DAQ", "Customer ID Number", req=True, length=25),
    # --- Dates ---
    "DBB": _f("DBB", "Date of Birth", dtype="N", length=8, req=True),
    "DBA": _f("DBA", "Document Expiration Date", dtype="N", length=8, req=True),
    "DBD": _f("DBD", "Document Issue Date", dtype="N", length=8, req=True),
    "DDB": _f("DDB", "Card Revision Date", dtype="N", length=8),
    "DDH": _f("DDH", "Date Cardholder Turns 18", dtype="N", length=8),
    "DDI": _f("DDI", "Date Cardholder Turns 19", dtype="N", length=8),
    "DDJ": _f("DDJ", "Date Cardholder Turns 21", dtype="N", length=8),
    # --- Physical description ---
    "DBC": _f("DBC", "Physical Description - Sex", dtype="N", length=1, req=True),
    "DAU": _f("DAU", "Physical Description - Height", length=6, req=True),
    "DAW": _f("DAW", "Physical Description - Weight", dtype="N", length=3),
    "DAY": _f("DAY", "Physical Description - Eye Color", dtype="A", length=3),
    "DAZ": _f("DAZ", "Hair Color", dtype="A", length=3),
    "DCE": _f("DCE", "Weight Range", dtype="N", length=1),
    "DCL": _f("DCL", "Race / Ethnicity", dtype="A", length=3),
    # --- Address ---
    "DAG": _f("DAG", "Address - Street 1", req=True),
    "DAH": _f("DAH", "Address - Street 2"),
    "DAI": _f("DAI", "Address - City", req=True),
    "DAJ": _f("DAJ", "Address - Jurisdiction Code", length=2, req=True),
    "DAK": _f("DAK", "Address - Postal Code", length=11, req=True),
    "DCG": _f("DCG", "Country Identification", dtype="A", length=3, req=True),
    # --- Vehicle / endorsement ---
    "DCA": _f("DCA", "Jurisdiction-specific Vehicle Class", "DL", length=6),
    "DCB": _f("DCB", "Jurisdiction-specific Restriction Codes", "DL", length=12),
    "DCD": _f("DCD", "Jurisdiction-specific Endorsement Codes", "DL", length=5),
    "DCM": _f("DCM", "Standard Vehicle Classification", length=4),
    "DCN": _f("DCN", "Standard Endorsement Code", length=5),
    "DCO": _f("DCO", "Standard Restriction Code", length=12),
    "DCP": _f("DCP", "Jurisdiction-specific Vehicle Classification", length=6),
    "DCQ": _f(
        "DCQ",
        "Jurisdiction-specific Endorsement Code Description",
        length=25,
    ),
    "DCR": _f(
        "DCR",
        "Jurisdiction-specific Restriction Code Description",
        length=25,
    ),
    # --- Document metadata ---
    "DCF": _f("DCF", "Document Discriminator", req=True, length=25),
    "DCK": _f("DCK", "Inventory Control Number", length=25),
    "DDA": _f("DDA", "Compliance Type", dtype="A", length=1),
    "DDD": _f("DDD", "Limited Duration Document Indicator", dtype="N", length=1),
    "DDC": _f("DDC", "HazMat Endorsement Expiration Date", dtype="N", length=8),
    "DCJ": _f("DCJ", "Audit Information", length=25),
    # --- Name truncation ---
    "DDE": _f("DDE", "Family Name Truncation", dtype="A", length=1),
    "DDF": _f("DDF", "First Name Truncation", dtype="A", length=1),
    "DDG": _f("DDG", "Middle Name Truncation", dtype="A", length=1),
    # --- Alias ---
    "DBN": _f("DBN", "Alias Family Name", length=40),
    "DBG": _f("DBG", "Alias Given Name", length=40),
    "DBS": _f("DBS", "Alias Suffix Name", length=10),
    # --- Miscellaneous ---
    "DCI": _f("DCI", "Place of Birth", length=33),
    "DDK": _f("DDK", "Organ Donor Indicator", dtype="N", length=1),
    "DDL": _f("DDL", "Veteran Indicator", dtype="N", length=1),
}

# Ordered list of element IDs in standard AAMVA output order.
FIELD_ORDER: list[str] = [
    "DCA",
    "DCB",
    "DCD",
    "DCS",
    "DAC",
    "DAD",
    "DBD",
    "DBB",
    "DBA",
    "DBC",
    "DAU",
    "DAY",
    "DAZ",
    "DAG",
    "DAH",
    "DAI",
    "DAJ",
    "DAK",
    "DAQ",
    "DCF",
    "DCG",
    "DCU",
    "DAW",
    "DCE",
    "DCL",
    "DCM",
    "DCN",
    "DCO",
    "DCP",
    "DCQ",
    "DCR",
    "DCK",
    "DCI",
    "DBN",
    "DBG",
    "DBS",
    "DDA",
    "DDB",
    "DDC",
    "DDD",
    "DDE",
    "DDF",
    "DDG",
    "DDH",
    "DDI",
    "DDJ",
    "DDK",
    "DDL",
    "DCJ",
]
