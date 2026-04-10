"""Tests for PDF417 encoder."""
import pytest

from canada_id.codec.encoder import (
    barcode_to_image,
    encode_pdf417,
)


def test_encode_simple_text():
    """Encoding simple text produces non-empty barcode."""
    barcode = encode_pdf417("HELLO WORLD")
    assert len(barcode) > 0
    assert len(barcode[0]) > 0


def test_encode_returns_2d_array():
    """Barcode is a 2D array of 0s and 1s."""
    barcode = encode_pdf417("TEST")
    for row in barcode:
        for cell in row:
            assert cell in (0, 1), f"Unexpected value: {cell}"


def test_encode_aamva_string():
    """Encoding an AAMVA-like string succeeds."""
    aamva = (
        "@\nANSI 636012090001DL00310242DL\n"
        "DCSSMITH\nDACJOHN\nDAQ12345\n"
    )
    barcode = encode_pdf417(aamva)
    assert len(barcode) > 0


def test_encode_numeric_data():
    """Numeric-heavy data triggers numeric compaction."""
    data = "1234567890123456789012345678901234567890"
    barcode = encode_pdf417(data)
    assert len(barcode) > 0


def test_encode_binary_data():
    """Binary data (bytes) can be encoded."""
    data = bytes(range(256)).decode("latin-1")
    barcode = encode_pdf417(data)
    assert len(barcode) > 0


def test_barcode_to_image():
    """Barcode converts to a valid PIL Image."""
    barcode = encode_pdf417("TEST IMAGE")
    img = barcode_to_image(barcode, scale=2)
    assert img.width > 0
    assert img.height > 0
    assert img.mode == "1"


def test_encode_empty_string_returns_empty():
    """Empty input returns empty list."""
    barcode = encode_pdf417("")
    assert barcode == []


def test_encode_with_explicit_ecl():
    """Explicit error correction level works."""
    barcode = encode_pdf417("TEST", ecl=5)
    assert len(barcode) > 0


def test_barcode_dimensions_reasonable():
    """Barcode dimensions are within expected range."""
    barcode = encode_pdf417("SHORT")
    rows = len(barcode)
    cols = len(barcode[0]) if barcode else 0
    assert 10 < rows < 500
    assert 50 < cols < 1000
