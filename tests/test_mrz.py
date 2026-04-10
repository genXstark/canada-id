"""Tests for MRZ generation, parsing, and AAMVA bridge (new API)."""
import pytest

from canada_id.mrz.aamva_bridge import aamva_to_mrz_data
from canada_id.mrz.checksum import compute, compute_str, verify
from canada_id.mrz.generator import MRZData, generate_mrz
from canada_id.mrz.models import MrzFormat, Sex
from canada_id.mrz.parsers import MrzParseError, parse_mrz, validate_mrz
from canada_id.mrz.renderer import render_mrz_image
from canada_id.mrz.utils import lines_from_mrz


class TestChecksum:
    """Tests for ICAO 9303 check digit algorithm."""

    def test_known_value(self):
        assert compute_str("AB1234567") == "1"

    def test_all_zeros(self):
        assert compute("000000") == 0

    def test_filler_chars(self):
        assert compute("<<<<<<") == 0

    def test_verify_valid(self):
        cd = compute_str("AB1234567")
        assert verify("AB1234567", cd)

    def test_verify_invalid(self):
        assert not verify("AB1234567", "9")

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError):
            compute("ab123")


class TestTD1:
    """Tests for TD1 (ID card) MRZ generation + parsing roundtrip."""

    @pytest.fixture
    def td1_data(self):
        return MRZData(
            document_type="I",
            country_code="CAN",
            surname="SMITH",
            given_names="JOHN MICHAEL",
            document_number="S12345678",
            nationality="CAN",
            date_of_birth="900115",
            sex="M",
            expiry_date="280115",
            optional_data_1="ON",
        )

    def test_td1_length(self, td1_data):
        mrz = generate_mrz(td1_data, "TD1")
        assert len(mrz) == 90

    def test_td1_lines(self, td1_data):
        mrz = generate_mrz(td1_data, "TD1")
        lines = lines_from_mrz(mrz)
        assert len(lines) == 3
        assert all(len(l) == 30 for l in lines)

    def test_td1_roundtrip(self, td1_data):
        mrz = generate_mrz(td1_data, "TD1")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid
        assert result.format == MrzFormat.TD1
        assert result.surname == "SMITH"
        assert result.given_names == "JOHN MICHAEL"
        assert result.issuing_country == "CAN"
        assert result.sex == Sex.MALE

    def test_td1_validate(self, td1_data):
        mrz = generate_mrz(td1_data, "TD1")
        assert validate_mrz(mrz, canada_only=True)


class TestTD2:
    """Tests for TD2 MRZ generation + parsing roundtrip."""

    @pytest.fixture
    def td2_data(self):
        return MRZData(
            document_type="I",
            country_code="CAN",
            surname="TREMBLAY",
            given_names="MARIE",
            document_number="X98765432",
            nationality="CAN",
            date_of_birth="850320",
            sex="F",
            expiry_date="270320",
        )

    def test_td2_length(self, td2_data):
        mrz = generate_mrz(td2_data, "TD2")
        assert len(mrz) == 72

    def test_td2_roundtrip(self, td2_data):
        mrz = generate_mrz(td2_data, "TD2")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid
        assert result.format == MrzFormat.TD2
        assert result.surname == "TREMBLAY"
        assert result.sex == Sex.FEMALE


class TestTD3:
    """Tests for TD3 (passport) MRZ generation + parsing roundtrip."""

    @pytest.fixture
    def td3_data(self):
        return MRZData(
            document_type="P",
            country_code="CAN",
            surname="DOE",
            given_names="JANE MARIE",
            document_number="AB1234567",
            nationality="CAN",
            date_of_birth="850320",
            sex="F",
            expiry_date="270320",
        )

    def test_td3_length(self, td3_data):
        mrz = generate_mrz(td3_data, "TD3")
        assert len(mrz) == 88

    def test_td3_lines(self, td3_data):
        mrz = generate_mrz(td3_data, "TD3")
        lines = lines_from_mrz(mrz)
        assert len(lines) == 2
        assert all(len(l) == 44 for l in lines)

    def test_td3_roundtrip(self, td3_data):
        mrz = generate_mrz(td3_data, "TD3")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid
        assert result.format == MrzFormat.TD3
        assert result.surname == "DOE"
        assert result.given_names == "JANE MARIE"

    def test_td3_validate(self, td3_data):
        mrz = generate_mrz(td3_data, "TD3")
        assert validate_mrz(mrz, canada_only=True)


class TestCanadaOnly:
    """Tests for canada_only flag."""

    def test_rejects_non_canadian(self):
        data = MRZData(
            document_type="P",
            country_code="USA",
            surname="TEST",
            given_names="USER",
            document_number="123456789",
            nationality="USA",
            date_of_birth="000101",
            sex="M",
            expiry_date="300101",
        )
        mrz = generate_mrz(data, "TD3")
        with pytest.raises(ValueError, match="Not a Canadian"):
            parse_mrz(mrz, canada_only=True)

    def test_allows_non_canadian_when_disabled(self):
        data = MRZData(
            document_type="P",
            country_code="USA",
            surname="TEST",
            given_names="USER",
            document_number="123456789",
            nationality="USA",
            date_of_birth="000101",
            sex="M",
            expiry_date="300101",
        )
        mrz = generate_mrz(data, "TD3")
        result = parse_mrz(mrz, canada_only=False)
        assert result.issuing_country == "USA"


class TestMrzFormat:
    """Tests for format detection and enum."""

    def test_invalid_format_raises(self):
        data = MRZData()
        with pytest.raises(ValueError):
            generate_mrz(data, "TD99")

    def test_format_enum_accepted(self):
        data = MRZData(
            surname="X", given_names="Y", document_number="1",
            date_of_birth="000101", expiry_date="300101",
        )
        mrz = generate_mrz(data, MrzFormat.TD1)
        assert len(mrz) == 90

    def test_bad_length_raises(self):
        with pytest.raises(MrzParseError):
            parse_mrz("TOOSHORT", canada_only=False)


class TestAAMVABridge:
    """Tests for AAMVA to MRZ conversion."""

    def test_aamva_to_mrz_basic(self, sample_on_fields):
        mrz_data = aamva_to_mrz_data(sample_on_fields)
        assert mrz_data.surname == "SMITH"
        assert mrz_data.country_code == "CAN"
        assert mrz_data.sex == "M"

    def test_aamva_to_td1_roundtrip(self, sample_on_fields):
        mrz_data = aamva_to_mrz_data(sample_on_fields)
        mrz = generate_mrz(mrz_data, "TD1")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid
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

    def test_render_produces_image(self):
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="ZZ9999999", nationality="CAN",
            date_of_birth="000101", sex="M", expiry_date="300101",
        )
        mrz = generate_mrz(data, "TD3")
        lines = lines_from_mrz(mrz)
        mrz_with_newlines = "\n".join(lines)
        img = render_mrz_image(mrz_with_newlines, scale=2)
        assert img.width > 0
        assert img.height > 0
        assert img.mode == "L"
