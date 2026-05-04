"""MRZ generator compatibility layer.

Provides the same API as mrz_generator_complete.py
but uses the project's native implementations.
"""
from __future__ import annotations

import random
import string
from datetime import datetime

from canada_id.mrz.generator import MRZData, generate_mrz
from canada_id.mrz.models import MrzFormat


def generate_passport_mrz(
    surname: str,
    given_names: str,
    passport_number: str,
    nationality: str,
    dob: str,
    sex: str,
    expiry_date: str,
) -> str:
    """Generate MRZ for Canadian Passport (TD3 format - 2 lines, 44 chars each).
    
    Args:
        surname: Last name (e.g., "SMITH")
        given_names: First and middle names (e.g., "JOHN ALEXANDER")
        passport_number: Passport number (e.g., "AB123456")
        nationality: "CAN"
        dob: Date of birth in YYMMDD format (e.g., "950523" for May 23, 1995)
        sex: "M" or "F"
        expiry_date: Expiry date in YYMMDD format (e.g., "310523")
    
    Returns:
        str: Two-line MRZ string with proper checksums
    
    Example:
        >>> mrz = generate_passport_mrz("SMITH", "JOHN ALEXANDER", "AB123456", "CAN", "950523", "M", "310523")
        >>> print(mrz)
        P<CANSMITH<<JOHN<ALEXANDER<<<<<<<<<<<<<<<<<<<<
        AB1234566CAN9505234M3105234<<<<<<<<<<<<<<06
    """
    data = MRZData(
        document_type="P",
        country_code="CAN",
        surname=surname.upper(),
        given_names=given_names.upper(),
        document_number=passport_number.upper(),
        nationality=nationality.upper(),
        date_of_birth=dob,
        sex=sex.upper(),
        expiry_date=expiry_date,
    )
    
    mrz_str = generate_mrz(data, MrzFormat.TD3)
    # Format as two lines of 44 characters each
    if len(mrz_str) == 88:
        return f"{mrz_str[:44]}\n{mrz_str[44:]}"
    return mrz_str


def generate_pr_card_mrz(
    surname: str,
    given_names: str,
    pr_number: str,
    dob: str,
    sex: str,
    expiry_date: str,
) -> str:
    """Generate MRZ for Permanent Resident Card (TD1 format - 3 lines, 30 chars each).
    
    Args:
        surname: Last name
        given_names: First and middle names
        pr_number: PR card number (10 digits)
        dob: YYMMDD
        sex: M/F
        expiry_date: YYMMDD
    
    Returns:
        str: Three-line MRZ string with proper checksums
    """
    data = MRZData(
        document_type="I",
        country_code="CAN",
        surname=surname.upper(),
        given_names=given_names.upper(),
        document_number=pr_number,
        nationality="CAN",
        date_of_birth=dob,
        sex=sex.upper(),
        expiry_date=expiry_date,
    )
    
    mrz_str = generate_mrz(data, MrzFormat.TD1)
    # Format as three lines of 30 characters each
    if len(mrz_str) == 90:
        return f"{mrz_str[:30]}\n{mrz_str[30:60]}\n{mrz_str[60:]}"
    return mrz_str


def generate_dl_mrz(
    surname: str,
    given_names: str,
    license_number: str,
    dob: str,
    sex: str,
    expiry_date: str,
    province: str = "ON",
) -> str:
    """Generate MRZ-style code for Driver's License (custom format).
    
    Note: Real Canadian DLs don't use MRZ, but this creates a compatible format.
    
    Args:
        surname: Last name
        given_names: First names
        license_number: License number
        dob: YYMMDD
        sex: M/F
        expiry_date: YYMMDD
        province: Province code (ON, QC, etc.)
    
    Returns:
        str: Three-line formatted string
    """
    # For DL, we create a custom format that looks like MRZ
    # This is for visual consistency, not actual MRZ standard
    line1 = f"DL{province}{license_number:<25}"[:30]
    line2 = f"{dob}{sex}{expiry_date}CAN{surname.upper():<10}"[:30]
    line3 = f"{given_names.upper().replace(' ', '<'):<30}"[:30]
    
    return f"{line1}\n{line2}\n{line3}"


def convert_date_format(
    date_str: str,
    input_format: str = "%Y-%m-%d",
    output_format: str = "%y%m%d",
) -> str:
    """Convert date between formats.
    
    Args:
        date_str: Date string (e.g., "1995-05-23" or "19950523")
        input_format: Input format (default: '%Y-%m-%d')
        output_format: Output format (default: '%y%m%d' for YYMMDD)
    
    Returns:
        str: Formatted date
    
    Examples:
        >>> convert_date_format("1995-05-23")
        '950523'
        >>> convert_date_format("2031-05-23")
        '310523'
    """
    try:
        dt = datetime.strptime(date_str, input_format)
        return dt.strftime(output_format)
    except ValueError:
        # Try other common formats
        for fmt in ["%Y%m%d", "%y%m%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime(output_format)
            except ValueError:
                continue
        # If all fail, return as-is
        return date_str


def generate_random_passport_number() -> str:
    """Generate random Canadian passport number (2 letters + 6 digits)."""
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    digits = "".join(random.choices(string.digits, k=6))
    return f"{letters}{digits}"


def generate_random_pr_number() -> str:
    """Generate random PR card number (10 digits)."""
    return "".join(random.choices(string.digits, k=10))


def generate_random_license_number(province: str = "ON") -> str:
    """Generate random license number based on province format.
    
    Ontario: Letter + 4 digits + 5 digits + 5 digits (S1234-56789-01234)
    Quebec: Letter + 4 digits + 6 digits + 2 digits (S1234-567890-12)
    """
    if province == "ON":
        letter = random.choice(string.ascii_uppercase)
        part1 = "".join(random.choices(string.digits, k=4))
        part2 = "".join(random.choices(string.digits, k=5))
        part3 = "".join(random.choices(string.digits, k=5))
        return f"{letter}{part1}-{part2}-{part3}"
    elif province == "QC":
        letter = random.choice(string.ascii_uppercase)
        part1 = "".join(random.choices(string.digits, k=4))
        part2 = "".join(random.choices(string.digits, k=6))
        part3 = "".join(random.choices(string.digits, k=2))
        return f"{letter}{part1}-{part2}-{part3}"
    else:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=12))


# For backwards compatibility with the original script
if __name__ == "__main__":
    print("=" * 60)
    print("MRZ GENERATOR TEST")
    print("=" * 60)
    
    # Test 1: Passport MRZ
    print("\n1. CANADIAN PASSPORT MRZ (TD3)")
    print("-" * 60)
    passport_mrz = generate_passport_mrz(
        surname="SMITH",
        given_names="JOHN ALEXANDER",
        passport_number="AB123456",
        nationality="CAN",
        dob="950523",  # May 23, 1995
        sex="M",
        expiry_date="310523",  # May 23, 2031
    )
    print(passport_mrz)
    lines = passport_mrz.split("\n")
    for i, line in enumerate(lines, 1):
        print(f"Line {i} length: {len(line)} chars")
    
    # Test 2: PR Card MRZ
    print("\n2. PERMANENT RESIDENT CARD MRZ (TD1)")
    print("-" * 60)
    pr_mrz = generate_pr_card_mrz(
        surname="SMITH",
        given_names="JOHN ALEXANDER",
        pr_number="1234567890",
        dob="950523",
        sex="M",
        expiry_date="310523",
    )
    print(pr_mrz)
    lines = pr_mrz.split("\n")
    for i, line in enumerate(lines, 1):
        print(f"Line {i} length: {len(line)} chars")
    
    # Test 3: Driver's License MRZ-style
    print("\n3. ONTARIO DRIVER'S LICENSE (Custom Format)")
    print("-" * 60)
    dl_mrz = generate_dl_mrz(
        surname="SMITH",
        given_names="JOHN ALEXANDER",
        license_number="S1234-56789-01234",
        dob="950523",
        sex="M",
        expiry_date="310523",
        province="ON",
    )
    print(dl_mrz)
    
    # Test 4: Date conversion
    print("\n4. DATE CONVERSION")
    print("-" * 60)
    test_dates = ["1995-05-23", "2031-05-23", "2000-01-01"]
    for date in test_dates:
        converted = convert_date_format(date)
        print(f"{date} → {converted}")
    
    # Test 5: Random generation
    print("\n5. RANDOM NUMBER GENERATION")
    print("-" * 60)
    print(f"Random Passport: {generate_random_passport_number()}")
    print(f"Random PR Card: {generate_random_pr_number()}")
    print(f"Random ON License: {generate_random_license_number('ON')}")
    print(f"Random QC License: {generate_random_license_number('QC')}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
