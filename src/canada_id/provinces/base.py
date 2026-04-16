"""Base province/territory profile dataclass.

All Canadian jurisdictions share ISO/IEC 7810 ID-1 card dimensions,
CCYYMMDD dates, metric height, and the Canadian postal code pattern.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProvinceProfile:
    """Immutable profile for a Canadian province or territory.

    Attributes:
        code: Two-letter abbreviation (e.g. "ON").
        name: Full English name (e.g. "Ontario").
        iin: Six-digit Issuer Identification Number.
        country: ISO 3166-1 alpha-3 country code.
        aamva_version: AAMVA specification version.
        date_format: Date encoding scheme.
        height_unit: Unit for physical height.
        postal_code_pattern: Regex for valid postal codes.
        required_fields: Frozenset of mandatory element IDs.
        optional_fields: Frozenset of optional element IDs.
        vehicle_classes: Mapping of class code to description.
        restriction_codes: Mapping of restriction code to description.
        endorsement_codes: Mapping of endorsement code to description.
        card_width_mm: Card width in millimeters.
        card_height_mm: Card height in millimeters.
        jurisdiction_version: Jurisdiction-specific version number.
    """

    code: str
    name: str
    iin: str
    country: str
    aamva_version: int
    date_format: str
    height_unit: str
    postal_code_pattern: str
    required_fields: frozenset[str]
    optional_fields: frozenset[str]
    vehicle_classes: dict[str, str]
    restriction_codes: dict[str, str]
    endorsement_codes: dict[str, str]
    card_width_mm: float
    card_height_mm: float
    jurisdiction_version: int


# Shared constants for all Canadian jurisdictions.
CAN_COUNTRY = "CAN"
CAN_DATE_FORMAT = "CCYYMMDD"
CAN_HEIGHT_UNIT = "cm"
CAN_POSTAL_PATTERN = r"^[A-Z]\d[A-Z] ?\d[A-Z]\d$"
CAN_CARD_WIDTH = 85.6
CAN_CARD_HEIGHT = 54.0
CAN_AAMVA_VERSION = 9

# Minimum required fields for all Canadian DLs.
CAN_REQUIRED_FIELDS = frozenset(
    {
        "DCS",
        "DAC",
        "DAQ",
        "DBB",
        "DBA",
        "DBD",
        "DBC",
        "DAU",
        "DAG",
        "DAI",
        "DAJ",
        "DAK",
        "DCG",
        "DCF",
    }
)

# Common optional fields.
CAN_OPTIONAL_FIELDS = frozenset(
    {
        "DAD",
        "DCU",
        "DAH",
        "DAY",
        "DAZ",
        "DAW",
        "DCA",
        "DCB",
        "DCD",
        "DDE",
        "DDF",
        "DDG",
        "DDB",
        "DDA",
        "DDD",
        "DDK",
        "DDL",
        "DCL",
    }
)
