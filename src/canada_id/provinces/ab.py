"""Alberta province profile."""

from canada_id.provinces.base import (
    CAN_AAMVA_VERSION,
    CAN_CARD_HEIGHT,
    CAN_CARD_WIDTH,
    CAN_COUNTRY,
    CAN_DATE_FORMAT,
    CAN_HEIGHT_UNIT,
    CAN_OPTIONAL_FIELDS,
    CAN_POSTAL_PATTERN,
    CAN_REQUIRED_FIELDS,
    ProvinceProfile,
)

PROFILE = ProvinceProfile(
    code="AB",
    name="Alberta",
    iin="604426",
    country=CAN_COUNTRY,
    aamva_version=CAN_AAMVA_VERSION,
    date_format=CAN_DATE_FORMAT,
    height_unit=CAN_HEIGHT_UNIT,
    postal_code_pattern=CAN_POSTAL_PATTERN,
    required_fields=CAN_REQUIRED_FIELDS,
    optional_fields=CAN_OPTIONAL_FIELDS,
    vehicle_classes={
        "1": "Semi-trailer truck",
        "2": "Bus (more than 24 passengers)",
        "3": "Large truck (single vehicle over 4,600 kg)",
        "4": "Taxi, ambulance, bus (24 or fewer passengers)",
        "5": "Cars, light trucks (under 4,600 kg)",
        "6": "Motorcycle",
    },
    restriction_codes={
        "A": "Corrective lenses",
        "B": "Mechanical aids",
        "C": "Daylight driving only",
        "D": "Speed limited",
        "E": "Automatic transmission",
    },
    endorsement_codes={
        "S": "School bus",
        "A": "Air brakes",
    },
    card_width_mm=CAN_CARD_WIDTH,
    card_height_mm=CAN_CARD_HEIGHT,
    jurisdiction_version=5,
)
