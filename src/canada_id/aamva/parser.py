"""AAMVA barcode string parser.

Splits a raw PDF417 barcode string into individual fields keyed
by their three-character AAMVA element ID.
"""

from __future__ import annotations

from canada_id.aamva.fields import FIELD_REGISTRY
from canada_id.aamva.header import AAMVAHeader, parse_header


def _extract_fields(data_lines: list[str]) -> dict[str, str]:
    """Extract element_id -> value pairs from data lines.

    Each line starts with a 3-char element ID followed by the value.
    The first data line may be prefixed with a subfile designator
    (e.g. "DL" or "ID") which is stripped.
    """
    fields: dict[str, str] = {}
    for line in data_lines:
        line = line.strip()
        if not line:
            continue
        # First data line after header may start with "DL" or "ID"
        # designator fused to the first field code.
        if len(line) >= 5 and line[:2] in ("DL", "ID"):
            candidate = line[2:5]
            if candidate in FIELD_REGISTRY:
                line = line[2:]
        if len(line) < 3:
            continue
        eid = line[:3]
        if eid in FIELD_REGISTRY:
            fields[eid] = line[3:]
    return fields


def parse_aamva(raw: str) -> dict[str, str]:
    """Parse a raw AAMVA barcode string into a field dictionary.

    Args:
        raw: Complete barcode string starting with '@'.

    Returns:
        Dict mapping element IDs to their string values.
    """
    lines = raw.split("\n")
    # Skip compliance indicator (@) and header line.
    data_lines = lines[2:] if len(lines) > 2 else []
    return _extract_fields(data_lines)


def parse_aamva_structured(
    raw: str,
) -> tuple[AAMVAHeader, dict[str, str]]:
    """Parse into header and field dict.

    Args:
        raw: Complete barcode string starting with '@'.

    Returns:
        Tuple of (AAMVAHeader, field dict).
    """
    header = parse_header(raw)
    fields = parse_aamva(raw)
    return header, fields
