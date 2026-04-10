"""AAMVA field validation against province profiles.

Checks required fields, date formats, field lengths, sex codes,
country/IIN consistency, and postal code format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from canada_id.aamva.fields import FIELD_REGISTRY
from canada_id.provinces.registry import get_profile


@dataclass
class ValidationError:
    """A single validation finding.

    Attributes:
        field: Element ID that failed validation (or "HEADER").
        message: Human-readable description of the issue.
        severity: "error" for hard failures, "warning" for advisories.
    """

    field: str
    message: str
    severity: str  # "error" | "warning"


def _check_required(
    fields: dict[str, str],
    required: frozenset[str],
    errors: list[ValidationError],
) -> None:
    """Flag any required fields that are missing or empty."""
    for eid in required:
        if eid not in fields or not fields[eid].strip():
            name = FIELD_REGISTRY[eid].name if eid in FIELD_REGISTRY else eid
            errors.append(ValidationError(
                eid, f"Required field missing: {name}", "error"
            ))


def _check_date_format(
    fields: dict[str, str],
    errors: list[ValidationError],
) -> None:
    """Validate CCYYMMDD date fields."""
    date_fields = ["DBB", "DBA", "DBD", "DDB", "DDH", "DDI", "DDJ", "DDC"]
    pattern = re.compile(r"^\d{8}$")
    for eid in date_fields:
        val = fields.get(eid, "")
        if not val:
            continue
        if not pattern.match(val):
            errors.append(ValidationError(
                eid, f"Date must be CCYYMMDD, got: {val!r}", "error"
            ))
            continue
        month = int(val[4:6])
        day = int(val[6:8])
        if month < 1 or month > 12:
            errors.append(ValidationError(
                eid, f"Invalid month {month} in date {val}", "error"
            ))
        if day < 1 or day > 31:
            errors.append(ValidationError(
                eid, f"Invalid day {day} in date {val}", "error"
            ))


def _check_lengths(
    fields: dict[str, str], errors: list[ValidationError]
) -> None:
    """Check that field values do not exceed max_length."""
    for eid, val in fields.items():
        defn = FIELD_REGISTRY.get(eid)
        if defn and len(val) > defn.max_length:
            errors.append(ValidationError(
                eid,
                f"{defn.name} exceeds max length {defn.max_length}"
                f" (got {len(val)})",
                "warning",
            ))


def _check_sex_code(
    fields: dict[str, str], errors: list[ValidationError]
) -> None:
    """Sex must be 1 (male), 2 (female), or 9 (not specified)."""
    val = fields.get("DBC", "")
    if val and val not in ("1", "2", "9"):
        errors.append(ValidationError(
            "DBC", f"Sex code must be 1, 2, or 9, got: {val!r}", "error"
        ))


def _check_province_consistency(
    fields: dict[str, str],
    province_code: str,
    errors: list[ValidationError],
) -> None:
    """Verify country and jurisdiction match the province profile."""
    profile = get_profile(province_code)

    country = fields.get("DCG", "")
    if country and country != profile.country:
        errors.append(ValidationError(
            "DCG",
            f"Country {country!r} does not match province "
            f"{province_code} (expected {profile.country!r})",
            "error",
        ))

    juris = fields.get("DAJ", "")
    if juris and juris != profile.code:
        errors.append(ValidationError(
            "DAJ",
            f"Jurisdiction {juris!r} does not match "
            f"province {profile.code!r}",
            "warning",
        ))

    postal = fields.get("DAK", "")
    if postal:
        pat = re.compile(profile.postal_code_pattern)
        cleaned = postal.strip()
        if not pat.match(cleaned):
            errors.append(ValidationError(
                "DAK",
                f"Postal code {cleaned!r} does not match "
                f"pattern for {province_code}",
                "warning",
            ))


def validate_aamva(
    fields: dict[str, str], province_code: str
) -> list[ValidationError]:
    """Validate AAMVA fields against a province profile.

    Args:
        fields: Element ID to value mapping.
        province_code: Two-letter province/territory code.

    Returns:
        List of ValidationError findings (may be empty).
    """
    profile = get_profile(province_code)
    errors: list[ValidationError] = []

    _check_required(fields, profile.required_fields, errors)
    _check_date_format(fields, errors)
    _check_lengths(fields, errors)
    _check_sex_code(fields, errors)
    _check_province_consistency(fields, province_code, errors)

    return errors
