"""Data models for MRZ parsing results.

Canada-only subset: TD1 (ID cards), TD2 (travel docs), TD3 (passports).
Ported from MRZParser-develop, stripped of French/Belgian/visa formats.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class MrzFormat(Enum):
    """Supported MRZ document formats (Canada-only)."""

    TD1 = "TD1"  # 3 x 30 (ID-1 cards)
    TD2 = "TD2"  # 2 x 36 (ID-2 documents)
    TD3 = "TD3"  # 2 x 44 (Passports)


class Sex(Enum):
    """Biological sex as encoded in MRZ."""

    MALE = "M"
    FEMALE = "F"
    UNSPECIFIED = "X"

    @classmethod
    def from_mrz(cls, value: str) -> Sex:
        """Parse MRZ sex character."""
        value = value.strip("<").upper()
        if value == "M":
            return cls.MALE
        if value == "F":
            return cls.FEMALE
        return cls.UNSPECIFIED


@dataclass(frozen=True)
class MrzResult:
    """Parsed MRZ data from any supported format."""

    format: MrzFormat
    document_type: str
    document_type_additional: str = ""
    issuing_country: str = ""
    surname: str = ""
    given_names: str = ""
    document_number: str = ""
    nationality: str = ""
    date_of_birth: str = ""
    sex: Sex = Sex.UNSPECIFIED
    expiry_date: str = ""
    birth_date: Optional[date] = None
    expiry_date_parsed: Optional[date] = None
    personal_number: str = ""
    optional_data_1: str = ""
    optional_data_2: str = ""
    check_digits_valid: bool = False
    raw_mrz: str = ""

    @property
    def is_canadian(self) -> bool:
        """Check if this document is issued by Canada."""
        return self.issuing_country == "CAN"

    def __str__(self) -> str:
        parts = [
            f"Format:           {self.format.value}",
            f"Document Type:    {self.document_type}"
            f"{self.document_type_additional}",
            f"Issuing Country:  {self.issuing_country}",
            f"Surname:          {self.surname}",
            f"Given Names:      {self.given_names}",
            f"Document Number:  {self.document_number}",
            f"Nationality:      {self.nationality}",
            f"Date of Birth:    {self.date_of_birth}"
            + (f"  ({self.birth_date})" if self.birth_date else ""),
            f"Sex:              {self.sex.value}",
            f"Expiry Date:      {self.expiry_date}"
            + (
                f"  ({self.expiry_date_parsed})"
                if self.expiry_date_parsed
                else ""
            ),
        ]
        if self.personal_number:
            parts.append(f"Personal Number:  {self.personal_number}")
        if self.optional_data_1:
            parts.append(f"Optional Data 1:  {self.optional_data_1}")
        if self.optional_data_2:
            parts.append(f"Optional Data 2:  {self.optional_data_2}")
        parts.append(f"Valid:            {self.check_digits_valid}")
        parts.append(f"Canadian:         {self.is_canadian}")
        return "\n".join(parts)
