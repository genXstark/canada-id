"""Structured MRZ validation with field-level reporting.

Validates MRZ fields before generation with clear, actionable
error messages. Based on ICAO 9303 field rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date


@dataclass
class MrzFieldResult:
    """Validation result for a single MRZ field."""

    field_name: str
    value: str
    valid: bool
    message: str = ""
    severity: str = "error"


@dataclass
class MrzValidationReport:
    """Full validation report for MRZ data."""

    results: list[MrzFieldResult] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """True if no errors (warnings OK)."""
        return all(
            r.valid or r.severity == "warning"
            for r in self.results
        )

    @property
    def errors(self) -> list[MrzFieldResult]:
        """All failed checks with severity=error."""
        return [
            r for r in self.results
            if not r.valid and r.severity == "error"
        ]

    @property
    def warnings(self) -> list[MrzFieldResult]:
        """All warnings."""
        return [
            r for r in self.results
            if not r.valid and r.severity == "warning"
        ]

    def summary(self) -> str:
        """Human-readable summary."""
        lines = []
        for r in self.results:
            if not r.valid:
                tag = "ERROR" if r.severity == "error" else "WARN"
                lines.append(
                    f"[{tag}] {r.field_name}: {r.message}"
                )
        if not lines:
            return "All fields valid."
        return "\n".join(lines)


_ALPHA_ONLY = re.compile(r"^[A-Z]+$")
_ALNUM = re.compile(r"^[A-Z0-9]+$")
_DATE = re.compile(r"^[0-9]{6}$")
_HONORIFICS = {
    "DR", "MR", "MRS", "MS", "MISS", "SIR", "DAME",
    "PROF", "REV", "HON", "CAPT", "SGT", "CPL",
}
# IRCC UCI / Client ID — 8 digits or 10 digits, optional dashes
# 0000-0000 (8) or 00-0000-0000 (10)
_UCI_RE = re.compile(r"^(\d{4}-?\d{4}|\d{2}-?\d{4}-?\d{4})$")
# Canadian passport doc# — both formats per IRCC May 2023 redesign
_PASSPORT_LEGACY = re.compile(r"^[A-Z]{2}\d{6}$")
_PASSPORT_NEW = re.compile(r"^[A-Z]\d{6}[A-Z]{2}$")
# PR card doc# — 2 letters + 7 digits (per Wikipedia + IRCC samples)
_PR_CARD_DOC_RE = re.compile(r"^[A-Z]{2}\d{7}$")


def validate_uci(uci: str) -> tuple[bool, str]:
    """Validate IRCC UCI / Client ID.

    Accepts 8-digit (0000-0000) or 10-digit (00-0000-0000) format,
    with or without dashes.

    Returns:
        (valid, message) tuple. message empty on valid.
    """
    if not uci:
        return False, "UCI is empty"
    cleaned = uci.replace(" ", "").upper()
    if not _UCI_RE.match(cleaned):
        return False, (
            f"Invalid UCI format. Expected 8 digits (0000-0000) or"
            f" 10 digits (00-0000-0000), got '{uci}'"
        )
    return True, ""


def validate_passport_number(num: str) -> tuple[bool, str]:
    """Validate Canadian passport document number.

    Accepts both pre-May 2023 (AB123456, 8 chars) and post-May 2023
    (A123456BC, 9 chars) formats.
    """
    if not num:
        return False, "Passport number is empty"
    cleaned = num.replace(" ", "").upper()
    if _PASSPORT_LEGACY.match(cleaned):
        return True, "Legacy format (pre-May 2023)"
    if _PASSPORT_NEW.match(cleaned):
        return True, "Current format (post-May 2023)"
    return False, (
        f"Invalid passport number. Expected 'AB123456' (legacy) or"
        f" 'A123456BC' (current), got '{num}'"
    )


def validate_pr_card_number(num: str) -> tuple[bool, str]:
    """Validate Canadian PR card document number.

    Format: 2 uppercase letters followed by 7 digits.
    """
    if not num:
        return False, "PR card number is empty"
    cleaned = num.replace(" ", "").upper()
    if _PR_CARD_DOC_RE.match(cleaned):
        return True, ""
    return False, (
        f"Invalid PR card number. Expected 2 letters + 7 digits"
        f" (e.g. PD0183017), got '{num}'"
    )


def validate_mrz_fields(
    document_type: str,
    country_code: str,
    surname: str,
    given_names: str,
    document_number: str,
    nationality: str,
    date_of_birth: str,
    sex: str,
    expiry_date: str,
    mrz_format: str = "TD1",
    optional_data_1: str = "",
    optional_data_2: str = "",
) -> MrzValidationReport:
    """Validate MRZ fields before generation.

    Returns a structured report with field-level results.
    """
    report = MrzValidationReport()

    # Document type
    if not document_type:
        report.results.append(MrzFieldResult(
            "Document Type", document_type, False,
            "Document type is required (P, I, A, C)",
        ))
    elif document_type[0] not in "PIAC":
        report.results.append(MrzFieldResult(
            "Document Type", document_type, False,
            f"'{document_type}' is not standard."
            " Expected P (passport), I (ID/PR),"
            " A (travel doc), or C (other).",
            "warning",
        ))
    else:
        report.results.append(MrzFieldResult(
            "Document Type", document_type, True,
        ))

    # Country code
    _check_code(
        report, "Issuing Country", country_code,
        "3-letter country code",
    )

    # Nationality
    _check_code(
        report, "Nationality", nationality,
        "3-letter nationality code",
    )

    # Surname
    if not surname or not surname.strip():
        report.results.append(MrzFieldResult(
            "Surname", surname, False,
            "Surname is required.",
        ))
    else:
        report.results.append(MrzFieldResult(
            "Surname", surname, True,
        ))
        # Check for honorifics
        parts = surname.upper().split()
        for part in parts:
            if part in _HONORIFICS:
                report.results.append(MrzFieldResult(
                    "Surname", surname, False,
                    f"Contains honorific '{part}'."
                    " Remove titles from MRZ names.",
                    "warning",
                ))
                break

    # Given names
    if not given_names or not given_names.strip():
        report.results.append(MrzFieldResult(
            "Given Names", given_names, False,
            "Given names required.",
            "warning",
        ))
    else:
        report.results.append(MrzFieldResult(
            "Given Names", given_names, True,
        ))

    # Document number
    if not document_number:
        report.results.append(MrzFieldResult(
            "Document Number", document_number, False,
            "Document number is required.",
        ))
    elif len(document_number) > 9:
        report.results.append(MrzFieldResult(
            "Document Number", document_number, False,
            f"Too long ({len(document_number)} chars,"
            f" max 9). Value: '{document_number}'",
        ))
    else:
        report.results.append(MrzFieldResult(
            "Document Number", document_number, True,
        ))

    # Date of birth
    _check_date(report, "Date of Birth", date_of_birth)

    # Expiry date
    _check_date(report, "Expiry Date", expiry_date)

    # Cross-check dates
    if (date_of_birth and expiry_date
            and _DATE.match(date_of_birth)
            and _DATE.match(expiry_date)):
        try:
            birth = _parse_yy_date(date_of_birth, is_birth=True)
            expiry = _parse_yy_date(expiry_date, is_birth=False)
            if expiry <= birth:
                report.results.append(MrzFieldResult(
                    "Date Cross-Check", "", False,
                    f"Expiry ({expiry}) is before or equal"
                    f" to birth ({birth}).",
                ))
            today = date.today()
            if expiry < today:
                report.results.append(MrzFieldResult(
                    "Expiry Check", "", False,
                    f"Document expired on {expiry}.",
                    "warning",
                ))
        except (ValueError, OverflowError):
            pass

    # Sex
    if sex not in ("M", "F", "X", "<", ""):
        report.results.append(MrzFieldResult(
            "Sex", sex, False,
            f"Invalid sex '{sex}'. Use M, F, or X.",
        ))
    else:
        report.results.append(MrzFieldResult(
            "Sex", sex, True,
        ))

    # Optional data length checks
    _check_optional(
        report, mrz_format, optional_data_1, optional_data_2,
    )

    return report


def _check_code(
    report: MrzValidationReport,
    name: str,
    value: str,
    desc: str,
) -> None:
    """Validate a 3-letter code field."""
    if not value:
        report.results.append(MrzFieldResult(
            name, value, False,
            f"{name} is required ({desc}).",
        ))
    elif len(value) != 3:
        report.results.append(MrzFieldResult(
            name, value, False,
            f"Must be exactly 3 letters, got"
            f" '{value}' ({len(value)} chars).",
        ))
    elif not _ALPHA_ONLY.match(value):
        report.results.append(MrzFieldResult(
            name, value, False,
            f"Must be letters only, got '{value}'.",
        ))
    else:
        report.results.append(MrzFieldResult(
            name, value, True,
        ))


def _check_date(
    report: MrzValidationReport,
    name: str,
    value: str,
) -> None:
    """Validate a YYMMDD date field."""
    if not value:
        report.results.append(MrzFieldResult(
            name, value, False,
            f"{name} is required (YYMMDD format).",
        ))
        return

    if not _DATE.match(value):
        report.results.append(MrzFieldResult(
            name, value, False,
            f"Must be 6 digits YYMMDD, got '{value}'.",
        ))
        return

    mm = int(value[2:4])
    dd = int(value[4:6])
    if mm < 1 or mm > 12:
        report.results.append(MrzFieldResult(
            name, value, False,
            f"Invalid month {mm:02d} in '{value}'.",
        ))
    elif dd < 1 or dd > 31:
        report.results.append(MrzFieldResult(
            name, value, False,
            f"Invalid day {dd:02d} in '{value}'.",
        ))
    else:
        report.results.append(MrzFieldResult(
            name, value, True,
        ))


def _check_optional(
    report: MrzValidationReport,
    mrz_format: str,
    opt1: str,
    opt2: str,
) -> None:
    """Check optional data field lengths per format."""
    limits = {
        "TD1": (15, 11),
        "TD2": (7, 0),
        "TD3": (14, 0),
    }
    max1, max2 = limits.get(mrz_format, (15, 11))

    if opt1 and len(opt1) > max1:
        report.results.append(MrzFieldResult(
            "Optional Data 1", opt1, False,
            f"Too long for {mrz_format}:"
            f" {len(opt1)} chars, max {max1}.",
        ))

    if opt2 and len(opt2) > max2:
        report.results.append(MrzFieldResult(
            "Optional Data 2", opt2, False,
            f"Too long for {mrz_format}:"
            f" {len(opt2)} chars, max {max2}.",
        ))


def _parse_yy_date(yymmdd: str, is_birth: bool) -> date:
    """Parse YYMMDD to date with century heuristic."""
    yy = int(yymmdd[:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])
    today = date.today()
    century = today.year // 100
    year = century * 100 + yy
    if is_birth and year > today.year:
        year -= 100
    if not is_birth and year < today.year - 10:
        year += 100
    return date(year, mm, dd)
