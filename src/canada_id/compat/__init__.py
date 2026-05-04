"""Compatibility layer for external script integration.

Provides API-compatible wrappers that match the interface of
external barcode and MRZ generator scripts while using
the project's native implementations.
"""

from canada_id.compat.barcode_compat import (
    generate_aamva_data,
    generate_code128,
    generate_code39,
    generate_pdf417,
    generate_qr_code,
)
from canada_id.compat.mrz_compat import (
    convert_date_format,
    generate_dl_mrz,
    generate_passport_mrz,
    generate_pr_card_mrz,
    generate_random_license_number,
    generate_random_passport_number,
    generate_random_pr_number,
)

__all__ = [
    # Barcode functions
    "generate_pdf417",
    "generate_code128", 
    "generate_code39",
    "generate_qr_code",
    "generate_aamva_data",
    # MRZ functions
    "generate_passport_mrz",
    "generate_pr_card_mrz",
    "generate_dl_mrz",
    "convert_date_format",
    "generate_random_passport_number",
    "generate_random_pr_number",
    "generate_random_license_number",
]
