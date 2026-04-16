"""MRZ (Machine Readable Zone) generation and parsing per ICAO 9303.

Canada-only: supports TD1, TD2, TD3 formats.
Includes ICAO transliteration, Canadian document definitions,
and structured field-level validation.
"""
from canada_id.mrz.canada_docs import (
    CANADIAN_DOCS,
    CanadianDocType,
    all_doc_types,
    doc_choices,
    get_doc_type,
)
from canada_id.mrz.checksum import compute, compute_str, verify
from canada_id.mrz.generator import MRZData, generate_mrz
from canada_id.mrz.models import MrzFormat, MrzResult, Sex
from canada_id.mrz.parsers import (
    MrzParseError,
    parse_mrz,
    validate_mrz,
)
from canada_id.mrz.renderer import render_mrz_image
from canada_id.mrz.transliterate import transliterate, transliterate_name
from canada_id.mrz.validate import (
    MrzFieldResult,
    MrzValidationReport,
    validate_mrz_fields,
)

__all__ = [
    "CANADIAN_DOCS",
    "CanadianDocType",
    "MRZData",
    "MrzFieldResult",
    "MrzFormat",
    "MrzParseError",
    "MrzResult",
    "MrzValidationReport",
    "Sex",
    "all_doc_types",
    "compute",
    "compute_str",
    "doc_choices",
    "generate_mrz",
    "get_doc_type",
    "parse_mrz",
    "render_mrz_image",
    "transliterate",
    "transliterate_name",
    "validate_mrz",
    "validate_mrz_fields",
    "verify",
]
