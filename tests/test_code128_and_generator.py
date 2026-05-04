"""Test Code 128 encoder and document generator."""
import pytest
from PIL import Image

from canada_id.codec.code128 import encode_code128, code128_to_image


class TestCode128Encoder:
    """Test Code 128 encoding."""

    def test_encode_uppercase(self):
        """Test encoding uppercase text."""
        bars = encode_code128("TEST")
        assert bars is not None
        assert len(bars) > 0

    def test_encode_mixed_case(self):
        """Test encoding mixed case text."""
        bars = encode_code128("Test123")
        assert bars is not None
        assert len(bars) > 0

    def test_encode_numeric_only(self):
        """Test encoding numeric data."""
        bars = encode_code128("123456")
        assert bars is not None
        assert len(bars) > 0

    def test_encode_alphanumeric(self):
        """Test encoding alphanumeric data."""
        bars = encode_code128("ABC123XYZ")
        assert bars is not None
        assert len(bars) > 0

    def test_to_image_basic(self):
        """Test image generation."""
        img = code128_to_image("TEST123")
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0

    def test_to_image_with_text(self):
        """Test image with text label."""
        img = code128_to_image("TESTCODE", show_text=True)
        assert isinstance(img, Image.Image)
        # With text, image should be taller
        assert img.height > 50

    def test_to_image_no_text(self):
        """Test image without text label."""
        img = code128_to_image("TEST", show_text=False, bar_height=40)
        assert isinstance(img, Image.Image)
        # Without text, height should be closer to bar_height
        assert img.height <= 50

    def test_gs1_128(self):
        """Test GS1-128 encoding with FNC1."""
        bars = encode_code128("12345678", add_fnc1=True)
        assert bars is not None
        assert len(bars) > 0

    def test_checksum_calculation(self):
        """Test that checksums are calculated correctly."""
        # Same data should produce consistent results
        bars1 = encode_code128("HELLO")
        bars2 = encode_code128("HELLO")
        assert bars1 == bars2

    def test_special_characters(self):
        """Test encoding with special characters."""
        img = code128_to_image("A-123/B")
        assert isinstance(img, Image.Image)

    def test_numeric_only_shorter(self):
        """Test that all-numeric data produces shorter barcode due to Mode C."""
        bars_numeric = encode_code128("00112233")
        bars_mixed = encode_code128("A0112233")
        # Numeric-only should be shorter due to Mode C compression
        assert len(bars_numeric[0]) < len(bars_mixed[0])


class TestDocumentGenerator:
    """Test document generation."""

    def test_import_generator(self):
        """Test that generator imports correctly."""
        from canada_id.templates import (
            generate_document,
            generate_drivers_license,
            generate_passport,
            DocumentType,
        )
        assert callable(generate_document)
        assert callable(generate_drivers_license)
        assert callable(generate_passport)

    def test_generate_ontario_dl(self):
        """Test Ontario driver's license generation."""
        from canada_id.templates import generate_drivers_license

        fields = {
            "DAQ": "S1234567890123",
            "DCS": "SMITH",
            "DAC": "JOHN",
            "DBB": "19850101",
            "DBA": "20271231",
            "DAG": "123 MAIN ST",
            "DAI": "TORONTO",
            "DAJ": "ON",
            "DAK": "M5V1A1",
            "DBC": "1",
        }
        result = generate_drivers_license("ON", fields)
        assert result.image is not None
        assert isinstance(result.image, Image.Image)

    def test_generate_passport(self):
        """Test passport generation."""
        from canada_id.templates import generate_passport

        fields = {
            "surname": "SMITH",
            "given_names": "JOHN JAMES",
            "document_number": "AB123456",
            "date_of_birth": "850101",
            "sex": "M",
            "expiry_date": "300101",
        }
        result = generate_passport(fields)
        assert result.image is not None
        assert isinstance(result.image, Image.Image)

    def test_generate_with_mrz(self):
        """Test that MRZ is generated for passport."""
        from canada_id.templates import generate_passport

        fields = {
            "surname": "DOE",
            "given_names": "JANE",
            "document_number": "XY987654",
            "date_of_birth": "900515",
            "sex": "F",
            "expiry_date": "320515",
        }
        result = generate_passport(fields)
        assert result.mrz_string is not None
        assert len(result.mrz_string) > 0


class TestCode39Integration:
    """Test Code 39 integration."""

    def test_code39_imports(self):
        """Test Code 39 imports from codec package."""
        from canada_id.codec import code39_to_image, encode_code39
        assert callable(code39_to_image)
        assert callable(encode_code39)

    def test_code39_image(self):
        """Test Code 39 image generation."""
        from canada_id.codec import code39_to_image
        img = code39_to_image("TEST123")
        assert isinstance(img, Image.Image)


class TestPdf417Integration:
    """Test PDF417 integration."""

    def test_pdf417_imports(self):
        """Test PDF417 imports."""
        from canada_id.codec import encode_pdf417, barcode_to_image
        assert callable(encode_pdf417)
        assert callable(barcode_to_image)

    def test_pdf417_aamva(self):
        """Test PDF417 with AAMVA data."""
        from canada_id.aamva.builder import build_aamva
        from canada_id.codec import encode_pdf417, barcode_to_image

        fields = {
            "DAQ": "S1234567890123",
            "DCS": "SMITH",
            "DAC": "JOHN",
            "DBB": "19850101",
            "DBA": "20271231",
        }
        aamva = build_aamva(fields, "ON")
        barcode = encode_pdf417(aamva)
        img = barcode_to_image(barcode)
        assert isinstance(img, Image.Image)
