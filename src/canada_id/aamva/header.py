"""AAMVA header block parsing and building.

Header format (version 9+):
  @\\n                          compliance indicator + separator
  ANSI                          file type (5 chars including trailing space)
  IIN                           issuer identification number (6 digits)
  AAMVA version                 (2 digits)
  jurisdiction version          (2 digits)
  number of entries             (2 digits)
  per entry: type(2) + offset(4) + length(4)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubfileEntry:
    """Pointer to a subfile within the AAMVA data.

    Attributes:
        subfile_type: Two-character designator (e.g. "DL", "ID", "ZC").
        offset: Byte offset from start of the string.
        length: Length in bytes of the subfile.
    """

    subfile_type: str
    offset: int
    length: int


@dataclass
class AAMVAHeader:
    """Parsed AAMVA file header.

    Attributes:
        iin: Six-digit issuer identification number.
        aamva_version: AAMVA version number (e.g. 9, 10).
        jurisdiction_version: Jurisdiction-specific version.
        num_entries: Count of subfile entries.
        subfiles: List of subfile pointers.
    """

    iin: str
    aamva_version: int
    jurisdiction_version: int
    num_entries: int
    subfiles: list[SubfileEntry]


_COMPLIANCE = "@"
_FILE_TYPE = "ANSI "
_HEADER_FIXED_LEN = 5 + 6 + 2 + 2 + 2  # file_type+IIN+ver+jver+entries = 17
_ENTRY_LEN = 10  # type(2) + offset(4) + length(4)


def parse_header(raw: str) -> AAMVAHeader:
    """Parse the AAMVA header block from a raw barcode string.

    Args:
        raw: Full AAMVA barcode string starting with '@'.

    Returns:
        Populated AAMVAHeader.

    Raises:
        ValueError: If the header cannot be parsed.
    """
    lines = raw.split("\n")
    if not lines or lines[0].strip() != _COMPLIANCE:
        raise ValueError("Missing compliance indicator '@'")
    if len(lines) < 2:
        raise ValueError("Missing header line after compliance indicator")

    hdr = lines[1]
    if not hdr.startswith(_FILE_TYPE):
        raise ValueError(f"Expected 'ANSI ' file type, got: {hdr[:5]!r}")

    pos = 5
    iin = hdr[pos : pos + 6]
    pos += 6
    aamva_ver = int(hdr[pos : pos + 2])
    pos += 2
    juris_ver = int(hdr[pos : pos + 2])
    pos += 2
    num_entries = int(hdr[pos : pos + 2])
    pos += 2

    subfiles: list[SubfileEntry] = []
    for _ in range(num_entries):
        stype = hdr[pos : pos + 2]
        pos += 2
        offset = int(hdr[pos : pos + 4])
        pos += 4
        length = int(hdr[pos : pos + 4])
        pos += 4
        subfiles.append(SubfileEntry(stype, offset, length))

    return AAMVAHeader(
        iin=iin,
        aamva_version=aamva_ver,
        jurisdiction_version=juris_ver,
        num_entries=num_entries,
        subfiles=subfiles,
    )


def build_header(header: AAMVAHeader) -> str:
    """Build an AAMVA header string from structured data.

    Args:
        header: Populated AAMVAHeader.

    Returns:
        Two-line string: compliance indicator line + header line.
    """
    parts = [
        _FILE_TYPE,
        header.iin,
        f"{header.aamva_version:02d}",
        f"{header.jurisdiction_version:02d}",
        f"{header.num_entries:02d}",
    ]
    for entry in header.subfiles:
        parts.append(entry.subfile_type)
        parts.append(f"{entry.offset:04d}")
        parts.append(f"{entry.length:04d}")

    return f"{_COMPLIANCE}\n{''.join(parts)}"
