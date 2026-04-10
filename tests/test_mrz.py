"""Tests for MRZ generation, parsing, and AAMVA bridge."""
import pytest

from canada_id.mrz.aamva_bridge import aamva_to_mrz_data
from canada_id.mrz.checkdigit import compute_check_digit, verify_check_digit
from canada_id.mrz.generator import MRZData, generate_mrz, generate_td1, generate_td3
from canada_id.mrz.parser import parse_mrz
from canada_id.mrz.renderer import render_mrz_image


class TestCheckDigit:
    """Tests for ICAO 9303 check digit algorithm."""

    def test_known_value(self):
        assert compute_check_digit("AB1234567") == "1"

    def test_all_zeros(self):
        assert compute_check_digit("000000") == "0"

    def test_filler_chars(self):
        assert compute_check_digit("<<<<<<") == "0"

    def test_verify_valid(self):
        field = "AB1234567"
        cd = compute_check_digit(field)
        assert verify_check_digit(field, cd)

    def test_verify_invalid(self):
        assert not verify_check_digit("AB1234567", "9")

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError):
            compute_check_digit("ab123")  # lowercase


class TestTD1Generator:
    """Tests for TD1 (ID card) MRZ generation."""

    @pytest.fixture
    def td1_data(self):
        return MRZData(
            document_type="I",
            country_code="CAN",
            surname="SMITH",
            given_names="JOHN MICHAEL",
            document_number="S12345678",
            nationality="CAN",
            date_of_birth="19900115",
            sex="M",
            expiry_date="20280115",
            optional_data_1="ON",
        )

    def test_td1_line_lengths(self, td1_data):
        mrz = generate_td1(td1_data)
        lines = mrz.split("\n")
        assert len(lines) == 3
        assert all(len(l) == 30 for l in lines)

    def test_td1_valid_check_digits(self, td1_data):
        mrz = generate_td1(td1_data)
        result = parse_mrz(mrz)
        assert result.valid
        assert result.errors == []

    def test_td1_name_extraction(self, td1_data):
        mrz = generate_td1(td1_data)
        result = parse_mrz(mrz)
        assert result.surname == "SMITH"
        assert result.given_names == "JOHN MICHAEL"

    def test_td1_country(self, td1_data):
        mrz = generate_td1(td1_data)
        result = parse_mrz(mrz)
        assert result.country_code == "CAN"


class TestTD3Generator:
    """Tests for TD3 (passport) MRZ generation."""

    @pytest.fixture
    def td3_data(self):
        return MRZData(
            document_type="P",
            country_code="CAN",
            surname="DOE",
            given_names="JANE MARIE",
            document_number="AB1234567",
            nationality="CAN",
            date_of_birth="19850320",
            sex="F",
            expiry_date="20270320",
        )

    def test_td3_line_lengths(self, td3_data):
        mrz = generate_td3(td3_data)
        lines = mrz.split("\n")
        assert len(lines) == 2
        assert all(len(l) == 44 for l in lines)

    def test_td3_valid_check_digits(self, td3_data):
        mrz = generate_td3(td3_data)
        result = parse_mrz(mrz)
        assert result.valid

    def test_td3_name(self, td3_data):
        mrz = generate_td3(td3_data)
        result = parse_mrz(mrz)
        assert result.surname == "DOE"
        assert result.given_names == "JANE MARIE"


class TestAAMVABridge:
    """Tests for AAMVA to MRZ conversion."""

    def test_aamva_to_mrz_basic(self, sample_on_fields):
        mrz_data = aamva_to_mrz_data(sample_on_fields)
        assert mrz_data.surname == "SMITH"
        assert mrz_data.country_code == "CAN"
        assert mrz_data.sex == "M"

    def test_aamva_to_td1_roundtrip(self, sample_on_fields):
        mrz_data = aamva_to_mrz_data(sample_on_fields)
        mrz = generate_td1(mrz_data)
        result = parse_mrz(mrz)
        assert result.valid
        assert result.surname == "SMITH"

    def test_sex_code_mapping(self):
        fields = {
            "DBC": "2", "DCS": "DOE", "DAC": "JANE",
            "DBB": "19850320", "DBA": "20270320", "DAQ": "123",
        }
        mrz_data = aamva_to_mrz_data(fields)
        assert mrz_data.sex == "F"


class TestRenderer:
    """Tests for MRZ image rendering."""

    def test_render_td1(self):
        mrz = "I<CANS123456780ON<<<<<<<<<<<<\n9001158M2801153CAN<<<<<<<<<<<9\nSMITH<<JOHN<MICHAEL<<<<<<<<<<<<"
        img = render_mrz_image(mrz, scale=2)
        assert img.width > 0
        assert img.height > 0
        assert img.mode == "L"

    def test_render_td3(self):
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="ZZ9999999", nationality="CAN",
            date_of_birth="20000101", sex="M", expiry_date="20300101",
        )
        mrz = generate_td3(data)
        img = render_mrz_image(mrz, scale=3)
        assert img.width > 0


class TestGenerateMRZ:
    """Tests for the unified generate_mrz function."""

    def test_td1_format(self):
        data = MRZData(
            surname="X", given_names="Y", document_number="1",
            date_of_birth="20000101", expiry_date="20300101",
        )
        mrz = generate_mrz(data, "TD1")
        assert len(mrz.split("\n")) == 3

    def test_td3_format(self):
        data = MRZData(
            document_type="P",
            surname="X", given_names="Y", document_number="1",
            date_of_birth="20000101", expiry_date="20300101",
        )
        mrz = generate_mrz(data, "TD3")
        assert len(mrz.split("\n")) == 2

    def test_invalid_format(self):
        data = MRZData()
        with pytest.raises(ValueError):
            generate_mrz(data, "TD99")
