"""Tests for AAMVA builder."""
from canada_id.aamva.builder import build_aamva
from canada_id.aamva.parser import parse_aamva


def test_build_produces_parseable_output(sample_on_fields):
    """Built AAMVA string can be parsed back."""
    aamva_str = build_aamva(sample_on_fields, "ON")
    parsed = parse_aamva(aamva_str)
    assert parsed["DCS"] == "SMITH"
    assert parsed["DAC"] == "JOHN"
    assert parsed["DAI"] == "TORONTO"


def test_build_includes_header(sample_on_fields):
    """Built string starts with AAMVA header."""
    aamva_str = build_aamva(sample_on_fields, "ON")
    assert aamva_str.startswith("@\n")
    assert "ANSI " in aamva_str
    assert "636012" in aamva_str


def test_build_uses_province_iin(sample_ab_fields):
    """Builder uses the correct IIN for the province."""
    aamva_str = build_aamva(sample_ab_fields, "AB")
    assert "604426" in aamva_str


def test_build_roundtrip_all_fields(sample_on_fields):
    """All non-empty fields survive a build -> parse roundtrip."""
    aamva_str = build_aamva(sample_on_fields, "ON")
    parsed = parse_aamva(aamva_str)
    for key, val in sample_on_fields.items():
        if val:
            assert parsed.get(key) == val, f"Field {key} mismatch"


def test_build_different_provinces(sample_on_fields, sample_ab_fields):
    """Different provinces produce different IINs."""
    on_str = build_aamva(sample_on_fields, "ON")
    ab_str = build_aamva(sample_ab_fields, "AB")
    assert "636012" in on_str
    assert "604426" in ab_str
