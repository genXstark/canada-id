"""AAMVA barcode string builder.

Assembles a complete PDF417-encodable string from a field dictionary
and province code.
"""

from __future__ import annotations

from canada_id.aamva.fields import FIELD_ORDER, FIELD_REGISTRY
from canada_id.aamva.header import AAMVAHeader, SubfileEntry, build_header
from canada_id.provinces.registry import get_profile


def _build_subfile_body(
    fields: dict[str, str], designator: str
) -> str:
    """Build the DL/ID subfile body lines in standard order.

    Args:
        fields: Element ID to value mapping.
        designator: Subfile designator (e.g. "DL").

    Returns:
        Newline-joined field lines prefixed with designator.
    """
    lines: list[str] = []
    # Emit fields in canonical AAMVA order, skip unknowns.
    for eid in FIELD_ORDER:
        if eid in fields:
            lines.append(f"{eid}{fields[eid]}")
    # Append any fields not in the standard order list.
    for eid, val in fields.items():
        if eid not in FIELD_ORDER and eid in FIELD_REGISTRY:
            lines.append(f"{eid}{val}")
    body = "\n".join(lines)
    return f"{designator}\n{body}" if lines else designator


def build_aamva(
    fields: dict[str, str],
    province_code: str,
    aamva_version: int = 9,
) -> str:
    """Build a complete AAMVA barcode string.

    Args:
        fields: Dict of element ID to value.
        province_code: Two-letter province/territory code.
        aamva_version: AAMVA spec version (default 9).

    Returns:
        Complete AAMVA string ready for PDF417 encoding.
    """
    profile = get_profile(province_code)
    iin = profile.iin
    juris_ver = profile.jurisdiction_version

    designator = "DL"
    body = _build_subfile_body(fields, designator)

    # Calculate offsets: header = "@\n" + header_line + "\n"
    # Header line: "ANSI " (5) + IIN (6) + ver (2) + jver (2)
    #   + entries (2) + entry (10) = 27
    # Plus "@\n" = 2, plus trailing "\n" after header = 1
    header_line_len = 5 + 6 + 2 + 2 + 2 + 10  # 27
    # offset = len("@\n") + header_line_len + len("\n")
    offset = 2 + header_line_len + 1
    body_len = len(body)

    header = AAMVAHeader(
        iin=iin,
        aamva_version=aamva_version,
        jurisdiction_version=juris_ver,
        num_entries=1,
        subfiles=[
            SubfileEntry(designator, offset, body_len),
        ],
    )

    header_str = build_header(header)
    return f"{header_str}\n{body}"
