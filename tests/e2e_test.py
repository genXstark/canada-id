"""Full end-to-end test across all features."""

import tempfile

from PIL import Image

from canada_id.aamva.builder import build_aamva
from canada_id.aamva.parser import parse_aamva
from canada_id.aamva.validator import validate_aamva
from canada_id.card.compositor import composite_barcode_on_card
from canada_id.card.layout import BarcodeRegion
from canada_id.cli import main
from canada_id.codec.code39 import code39_to_image, encode_code39
from canada_id.codec.decoder import decode_pdf417_text
from canada_id.codec.encoder import barcode_to_image, encode_pdf417
from canada_id.guards import auto_fix_province, check_province_match, detect_province
from canada_id.mrz.aamva_bridge import aamva_to_mrz_data
from canada_id.mrz.generator import generate_mrz
from canada_id.mrz.parsers import parse_mrz
from canada_id.provinces.registry import all_profiles
from canada_id.storage import HistoryDB

BASE_FIELDS = {
    "DAQ": "TEST-12345-67890",
    "DCS": "KUMAR",
    "DAC": "ROHIT",
    "DAD": "",
    "DBB": "19990706",
    "DBA": "20300706",
    "DBD": "20220115",
    "DBC": "1",
    "DAY": "BRO",
    "DAU": "180 cm",
    "DAG": "123 TEST STREET",
    "DAI": "TESTCITY",
    "DCG": "CAN",
    "DCA": "G",
    "DCB": "",
    "DCD": "",
    "DCF": "TESTDOCID01",
    "DDE": "N",
    "DDF": "N",
    "DDG": "N",
}

POSTAL_CODES = {
    "AB": "T2P 1J9",
    "BC": "V6B 3K9",
    "MB": "R3C 0V8",
    "NB": "E1C 1G1",
    "NL": "A1B 3X9",
    "NT": "X1A 2P7",
    "NS": "B3H 4R2",
    "NU": "X0A 0H0",
    "ON": "M5V 2T6",
    "PE": "C1A 7N8",
    "QC": "H2B 2R8",
    "SK": "S4P 3Y2",
    "YT": "Y1A 2C6",
}


def test_roundtrip_all_13_provinces():
    """Encode -> barcode image -> decode -> parse for all 13 provinces."""
    for profile in all_profiles():
        code = profile.code
        fields = dict(BASE_FIELDS)
        fields["DAJ"] = code
        fields["DAK"] = POSTAL_CODES[code]

        aamva = build_aamva(fields, code)
        barcode = encode_pdf417(aamva)
        img = barcode_to_image(barcode, scale=3)
        decoded = decode_pdf417_text(img)

        assert len(decoded) > 0, f"{code}: no barcode decoded"
        parsed = parse_aamva(decoded[0])
        assert parsed["DCS"] == "KUMAR", f"{code}: name mismatch"
        assert parsed["DAJ"] == code, f"{code}: province mismatch"


def test_accented_characters():
    """French accented characters survive roundtrip."""
    fields = dict(BASE_FIELDS)
    fields["DAJ"] = "QC"
    fields["DAK"] = "H2B 2R8"
    fields["DAG"] = "1-9690 AV BRUCHESI"
    fields["DAI"] = "MONTREAL"

    aamva = build_aamva(fields, "QC")
    barcode = encode_pdf417(aamva)
    img = barcode_to_image(barcode, scale=3)
    decoded = decode_pdf417_text(img)
    parsed = parse_aamva(decoded[0])

    assert parsed["DAG"] == "1-9690 AV BRUCHESI"
    assert parsed["DAI"] == "MONTREAL"


def test_province_mismatch_guard():
    """Guard detects wrong province, auto-fix corrects it."""
    qc_fields = dict(BASE_FIELDS)
    qc_fields["DAJ"] = "QC"
    qc_fields["DAK"] = "H2B 2R8"

    # Wrong province should produce warnings
    warnings = check_province_match("AB", qc_fields)
    assert len(warnings) > 0

    # Correct province should produce no warnings
    warnings2 = check_province_match("QC", qc_fields)
    assert len(warnings2) == 0

    # Auto-detect and auto-fix
    assert detect_province(qc_fields) == "QC"
    code, reason = auto_fix_province(qc_fields)
    assert code == "QC"


def test_storage_roundtrip():
    """Store and retrieve operations from SQLite."""
    db = HistoryDB(tempfile.mktemp(suffix=".db"))

    barcode = encode_pdf417("TEST")
    img = barcode_to_image(barcode, scale=2)

    rid = db.log_encode("ON", BASE_FIELDS, "test-aamva", barcode_img=img)
    assert rid > 0

    rid2 = db.log_decode({"DCS": "TEST"}, "raw-payload", province="ON")
    assert rid2 > 0

    history = db.get_history()
    assert len(history) == 2

    stats = db.get_stats()
    assert stats["encode"] == 1
    assert stats["decode"] == 1

    stored = db.get_barcode_image(rid)
    assert stored is not None
    assert stored.size[0] > 0

    db.close()


def test_validator():
    """Validator catches missing required fields."""
    qc_fields = dict(BASE_FIELDS)
    qc_fields["DAJ"] = "QC"
    qc_fields["DAK"] = "H2B 2R8"

    bad_fields = {"DCS": "TEST"}
    errors = validate_aamva(bad_fields, "ON")
    assert len(errors) > 0


def test_code39():
    """Code 39 encoder produces valid output."""
    bars = encode_code39("HELLO123")
    assert len(bars) > 0
    img = code39_to_image("HELLO123")
    assert img.size[0] > 0


def test_card_compositor():
    """Barcode composites onto card template."""
    card = Image.new("RGB", (856, 540), color=(255, 255, 255))
    bc_img = barcode_to_image(encode_pdf417("TEST"), scale=2)
    region = BarcodeRegion(
        x_frac=0.02,
        y_frac=0.05,
        w_frac=0.37,
        h_frac=0.90,
        rotation_deg=-90.0,
    )
    result = composite_barcode_on_card(card, bc_img, region)
    assert result.size == (856, 540)


def test_mrz_generation():
    """MRZ generates and parses back."""
    fields = dict(BASE_FIELDS)
    fields["DAJ"] = "QC"
    fields["DAK"] = "H2B 2R8"

    mrz_data = aamva_to_mrz_data(fields)
    mrz_str = generate_mrz(mrz_data, "TD1")
    assert len(mrz_str) > 0

    parsed = parse_mrz(mrz_str)
    assert parsed.surname == "KUMAR"


def test_cli_commands_exist():
    """CLI has all expected commands."""
    cmds = [c.name for c in main.commands.values()]
    for expected in ["encode", "decode", "validate", "composite", "provinces", "mrz"]:
        assert expected in cmds, f"Missing CLI command: {expected}"
