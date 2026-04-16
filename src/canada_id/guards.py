"""Province mismatch detection.

Auto-detects province from AAMVA field data and warns when
the selected province doesn't match. Catches ADHD-friendly
mistakes like selecting Alberta but entering Quebec data.
"""

from __future__ import annotations

from dataclasses import dataclass

# Canadian postal code first letter -> province code(s)
_POSTAL_TO_PROVINCE: dict[str, str] = {
    "A": "NL",
    "B": "NS",
    "C": "PE",
    "E": "NB",
    "G": "QC",
    "H": "QC",
    "J": "QC",
    "K": "ON",
    "L": "ON",
    "M": "ON",
    "N": "ON",
    "P": "ON",
    "R": "MB",
    "S": "SK",
    "T": "AB",
    "V": "BC",
    "X": "NT",  # NT and NU share X prefix
    "Y": "YT",
}

# NU also uses X prefix
_POSTAL_AMBIGUOUS = {"X": ("NT", "NU")}


@dataclass
class MismatchWarning:
    """A detected province mismatch."""

    field: str
    expected: str
    actual: str
    message: str
    severity: str = "error"


def detect_province(fields: dict[str, str]) -> str | None:
    """Best-effort province detection from field data.

    Checks DAJ (jurisdiction code) first, then postal code prefix.

    Args:
        fields: AAMVA field dictionary.

    Returns:
        Two-letter province code, or None if indeterminate.
    """
    # DAJ is the jurisdiction code — most reliable
    daj = fields.get("DAJ", "").strip().upper()
    if len(daj) == 2:
        return daj

    # Fall back to postal code first letter
    dak = fields.get("DAK", "").strip().upper()
    if dak:
        first = dak[0]
        if first in _POSTAL_TO_PROVINCE:
            return _POSTAL_TO_PROVINCE[first]

    return None


def check_province_match(
    selected_province: str,
    fields: dict[str, str],
) -> list[MismatchWarning]:
    """Check if field data matches the selected province.

    Args:
        selected_province: The province code chosen by the user.
        fields: AAMVA field dictionary.

    Returns:
        List of mismatch warnings (empty if everything matches).
    """
    warnings: list[MismatchWarning] = []
    selected = selected_province.upper()

    # Check DAJ (jurisdiction code)
    daj = fields.get("DAJ", "").strip().upper()
    if daj and len(daj) == 2 and daj != selected:
        warnings.append(
            MismatchWarning(
                field="DAJ",
                expected=selected,
                actual=daj,
                message=(
                    f"Jurisdiction code is '{daj}' but you selected"
                    f" '{selected}'. Your data is for {daj}, not {selected}."
                ),
                severity="error",
            )
        )

    # Check postal code prefix
    dak = fields.get("DAK", "").strip().upper()
    if dak:
        first = dak[0]
        if first in _POSTAL_AMBIGUOUS:
            valid_provinces = _POSTAL_AMBIGUOUS[first]
            if selected not in valid_provinces:
                warnings.append(
                    MismatchWarning(
                        field="DAK",
                        expected=selected,
                        actual=f"{first}... (matches {'/'.join(valid_provinces)})",
                        message=(
                            f"Postal code '{dak}' starts with '{first}'"
                            f" which belongs to {'/'.join(valid_provinces)},"
                            f" not {selected}."
                        ),
                        severity="error",
                    )
                )
        elif first in _POSTAL_TO_PROVINCE:
            postal_province = _POSTAL_TO_PROVINCE[first]
            if postal_province != selected:
                warnings.append(
                    MismatchWarning(
                        field="DAK",
                        expected=selected,
                        actual=postal_province,
                        message=(
                            f"Postal code '{dak}' starts with '{first}'"
                            f" which belongs to {postal_province},"
                            f" not {selected}."
                        ),
                        severity="error",
                    )
                )

    # Check DAI (city) — just a soft warning for known province capitals
    # if other checks already flagged issues
    dai = fields.get("DAI", "").strip().upper()
    if dai and daj and daj != selected and not warnings:
        warnings.append(
            MismatchWarning(
                field="DAI",
                expected=selected,
                actual=daj,
                message=f"City '{dai}' appears to be in {daj}, not {selected}.",
                severity="warning",
            )
        )

    return warnings


def auto_fix_province(
    fields: dict[str, str],
) -> tuple[str | None, str]:
    """Detect province from fields and return suggested code + reason.

    Args:
        fields: AAMVA field dictionary.

    Returns:
        Tuple of (province_code, reason_string).
        province_code is None if detection fails.
    """
    daj = fields.get("DAJ", "").strip().upper()
    if len(daj) == 2:
        return daj, f"Auto-detected from jurisdiction code (DAJ={daj})"

    dak = fields.get("DAK", "").strip().upper()
    if dak:
        first = dak[0]
        if first in _POSTAL_TO_PROVINCE:
            code = _POSTAL_TO_PROVINCE[first]
            return code, f"Auto-detected from postal code prefix ({first}→{code})"

    return None, "Could not auto-detect province from fields"
