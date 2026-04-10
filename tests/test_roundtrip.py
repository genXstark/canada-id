"""Roundtrip tests: build AAMVA -> encode PDF417 -> decode -> parse -> assert."""
import pytest

from canada_id.aamva.builder import build_aamva
from canada_id.aamva.parser import parse_aamva
from canada_id.codec.decoder import decode_pdf417_text
from canada_id.codec.encoder import barcode_to_image, encode_pdf417
from canada_id.provinces.registry import all_profiles


def _roundtrip(fields: dict[str, str], province_code: str):
    """Run a full roundtrip test for given fields and province."""
    aamva_str = build_aamva(fields, province_code)
    barcode = encode_pdf417(aamva_str)
    img = barcode_to_image(barcode, scale=3)
    decoded = decode_pdf417_text(img)
    assert len(decoded) > 0, "No barcode decoded"
    parsed = parse_aamva(decoded[0])
    return parsed


def test_roundtrip_ontario(sample_on_fields):
    """Full roundtrip for Ontario."""
    parsed = _roundtrip(sample_on_fields, "ON")
    assert parsed["DCS"] == "SMITH"
    assert parsed["DAC"] == "JOHN"
    assert parsed["DAI"] == "TORONTO"
    assert parsed["DAJ"] == "ON"
    assert parsed["DCG"] == "CAN"


def test_roundtrip_alberta(sample_ab_fields):
    """Full roundtrip for Alberta."""
    parsed = _roundtrip(sample_ab_fields, "AB")
    assert parsed["DCS"] == "DOE"
    assert parsed["DAC"] == "JANE"
    assert parsed["DAI"] == "CALGARY"
    assert parsed["DAJ"] == "AB"


def test_roundtrip_preserves_all_nonempty_fields(sample_on_fields):
    """All non-empty fields survive the roundtrip."""
    parsed = _roundtrip(sample_on_fields, "ON")
    for key, val in sample_on_fields.items():
        if val:
            assert parsed.get(key) == val, (
                f"Field {key}: expected {val!r}, got {parsed.get(key)!r}"
            )


@pytest.mark.parametrize("province", [p.code for p in all_profiles()])
def test_roundtrip_all_provinces(province):
    """Basic roundtrip works for every province."""
    fields = {
        "DAQ": "TEST-123-456",
        "DCS": "TESTLAST",
        "DAC": "TESTFIRST",
        "DAD": "",
        "DBB": "19950101",
        "DBA": "20300101",
        "DBD": "20250101",
        "DBC": "1",
        "DAY": "BRO",
        "DAU": "175 cm",
        "DAG": "100 TEST STREET",
        "DAI": "TESTCITY",
        "DAJ": province,
        "DAK": "A1A 1A1",
        "DCG": "CAN",
        "DCA": "G",
        "DCB": "",
        "DCD": "",
        "DCF": "0000000000",
        "DDE": "N",
        "DDF": "N",
        "DDG": "N",
    }
    parsed = _roundtrip(fields, province)
    assert parsed["DCS"] == "TESTLAST"
    assert parsed["DAJ"] == province
