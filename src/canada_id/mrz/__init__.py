"""MRZ (Machine Readable Zone) generation and parsing per ICAO 9303.

Canada-only: supports TD1, TD2, TD3 formats.
"""
from canada_id.mrz.checksum import compute, compute_str, verify
from canada_id.mrz.generator import MRZData, generate_mrz
from canada_id.mrz.models import MrzFormat, MrzResult, Sex
from canada_id.mrz.parsers import (
    MrzParseError,
    parse_mrz,
    validate_mrz,
)
from canada_id.mrz.renderer import render_mrz_image

__all__ = [
    "MRZData",
    "MrzFormat",
    "MrzParseError",
    "MrzResult",
    "Sex",
    "compute",
    "compute_str",
    "generate_mrz",
    "parse_mrz",
    "render_mrz_image",
    "validate_mrz",
    "verify",
]
