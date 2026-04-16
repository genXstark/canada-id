"""Tests for province profiles."""

import re

import pytest

from canada_id.provinces.registry import all_profiles, get_profile, get_profile_by_iin

EXPECTED_CODES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NT",
    "NS",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}


def test_all_13_provinces_present():
    """All 13 Canadian provinces/territories have profiles."""
    profiles = all_profiles()
    codes = {p.code for p in profiles}
    assert codes == EXPECTED_CODES


def test_all_profiles_have_valid_iin():
    """Every profile has a 6-digit IIN."""
    for p in all_profiles():
        assert re.match(r"^\d{6}$", p.iin), f"{p.code} has invalid IIN: {p.iin}"


def test_all_profiles_use_can_country():
    """All Canadian profiles use CAN as country."""
    for p in all_profiles():
        assert p.country == "CAN", f"{p.code} has country {p.country}"


def test_all_profiles_use_ccyymmdd():
    """All Canadian profiles use CCYYMMDD date format."""
    for p in all_profiles():
        assert p.date_format == "CCYYMMDD", f"{p.code}: {p.date_format}"


def test_all_profiles_use_cm():
    """All Canadian profiles use centimeters for height."""
    for p in all_profiles():
        assert p.height_unit == "cm", f"{p.code}: {p.height_unit}"


def test_get_profile_by_code():
    """Lookup by code returns correct profile."""
    on = get_profile("ON")
    assert on.name == "Ontario"
    assert on.iin == "636012"


def test_get_profile_case_insensitive():
    """Profile lookup is case-insensitive."""
    on = get_profile("on")
    assert on.code == "ON"


def test_get_profile_invalid():
    """Invalid province code raises KeyError."""
    with pytest.raises(KeyError):
        get_profile("XX")


def test_get_profile_by_iin():
    """Lookup by IIN returns correct profile."""
    profile = get_profile_by_iin("636012")
    assert profile.code == "ON"


def test_all_profiles_have_vehicle_classes():
    """Every profile has at least one vehicle class."""
    for p in all_profiles():
        assert len(p.vehicle_classes) > 0, f"{p.code} has no vehicle classes"


def test_all_profiles_have_required_fields():
    """Every profile has required fields defined."""
    for p in all_profiles():
        assert len(p.required_fields) > 0, f"{p.code} has no required fields"


def test_card_dimensions():
    """Card dimensions are ISO ID-1 standard."""
    for p in all_profiles():
        assert abs(p.card_width_mm - 85.6) < 0.1, f"{p.code} width"
        assert abs(p.card_height_mm - 54.0) < 0.1, f"{p.code} height"
