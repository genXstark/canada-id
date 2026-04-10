"""Tests for AAMVA parser."""
import pytest

from canada_id.aamva.parser import parse_aamva, parse_aamva_structured


SAMPLE_AAMVA = (
    "@\n"
    "ANSI 636012090001DL00310242DL\n"
    "DCAG\n"
    "DCB\n"
    "DCD\n"
    "DBAEXPDATE\n"
    "DCSSMITH\n"
    "DACJOHN\n"
    "DADMICHAEL\n"
    "DBD20240115\n"
    "DBB19900115\n"
    "DBC1\n"
    "DAYBRO\n"
    "DAU180 cm\n"
    "DAG123 MAIN STREET\n"
    "DAITORONTO\n"
    "DAJON\n"
    "DAKM5V 2T6\n"
    "DAQS1234-56789-01234\n"
    "DCF0000000000\n"
    "DCGCAN\n"
    "DDEN\n"
    "DDFN\n"
    "DDGN\n"
)


def test_parse_extracts_fields():
    """Parser extracts known fields."""
    fields = parse_aamva(SAMPLE_AAMVA)
    assert fields["DCS"] == "SMITH"
    assert fields["DAC"] == "JOHN"
    assert fields["DAD"] == "MICHAEL"
    assert fields["DAG"] == "123 MAIN STREET"
    assert fields["DAI"] == "TORONTO"
    assert fields["DAJ"] == "ON"
    assert fields["DCG"] == "CAN"


def test_parse_sex_code():
    """Parser extracts sex code correctly."""
    fields = parse_aamva(SAMPLE_AAMVA)
    assert fields["DBC"] == "1"


def test_parse_dates():
    """Parser extracts date fields."""
    fields = parse_aamva(SAMPLE_AAMVA)
    assert fields["DBB"] == "19900115"
    assert fields["DBD"] == "20240115"


def test_parse_height():
    """Parser extracts height with unit."""
    fields = parse_aamva(SAMPLE_AAMVA)
    assert fields["DAU"] == "180 cm"


def test_parse_structured_returns_header():
    """Structured parser returns header and fields."""
    header, fields = parse_aamva_structured(SAMPLE_AAMVA)
    assert header.iin == "636012"
    assert header.aamva_version == 9
    assert fields["DCS"] == "SMITH"


def test_parse_empty_string():
    """Empty input returns empty dict."""
    fields = parse_aamva("")
    assert fields == {}


def test_parse_id_number():
    """Parser extracts customer ID number."""
    fields = parse_aamva(SAMPLE_AAMVA)
    assert fields["DAQ"] == "S1234-56789-01234"
