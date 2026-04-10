"""Nova Scotia province profile."""

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
    code="NS",
    name="Nova Scotia",
    iin="636013",
    country=CAN_COUNTRY,
    aamva_version=CAN_AAMVA_VERSION,
    date_format=CAN_DATE_FORMAT,
    height_unit=CAN_HEIGHT_UNIT,
    postal_code_pattern=CAN_POSTAL_PATTERN,
    required_fields=CAN_REQUIRED_FIELDS,
    optional_fields=CAN_OPTIONAL_FIELDS,
    vehicle_classes={
        "1": "Tractor-trailer",
        "2": "Bus (more than 24 passengers)",
        "3": "Non-articulated vehicle over 4,500 kg",
        "4": "Bus (24 or fewer passengers), ambulance, taxi",
        "5": "Two-axle vehicle under 4,500 kg",
        "6": "Motorcycle",
        "7": "Moped",
        "8": "Farm tractor",
        "9": "Construction equipment",
    },
    restriction_codes={
        "A": "Corrective lenses",
        "B": "Mechanical aids",
        "C": "Daylight driving only",
        "E": "Automatic transmission",
        "F": "Outside mirrors",
    },
    endorsement_codes={
        "S": "School bus",
        "A": "Air brakes",
    },
    card_width_mm=CAN_CARD_WIDTH,
    card_height_mm=CAN_CARD_HEIGHT,
    jurisdiction_version=3,
)
