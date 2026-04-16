"""Shared test fixtures for canada-id."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_AAMVA_DIR = FIXTURES_DIR / "sample_aamva"
SAMPLE_BARCODES_DIR = FIXTURES_DIR / "sample_barcodes"


@pytest.fixture
def sample_on_fields() -> dict[str, str]:
    """Sample Ontario AAMVA field data."""
    return {
        "DAQ": "S1234-56789-01234",
        "DCS": "SMITH",
        "DAC": "JOHN",
        "DAD": "MICHAEL",
        "DBB": "19900115",
        "DBA": "20280115",
        "DBD": "20240115",
        "DBC": "1",
        "DAY": "BRO",
        "DAU": "180 cm",
        "DAG": "123 MAIN STREET",
        "DAI": "TORONTO",
        "DAJ": "ON",
        "DAK": "M5V 2T6",
        "DCG": "CAN",
        "DCA": "G",
        "DCB": "",
        "DCD": "",
        "DCF": "0000000000",
        "DDE": "N",
        "DDF": "N",
        "DDG": "N",
    }


@pytest.fixture
def sample_ab_fields() -> dict[str, str]:
    """Sample Alberta AAMVA field data."""
    return {
        "DAQ": "123456-789",
        "DCS": "DOE",
        "DAC": "JANE",
        "DAD": "MARIE",
        "DBB": "19850320",
        "DBA": "20270320",
        "DBD": "20230320",
        "DBC": "2",
        "DAY": "GRN",
        "DAU": "165 cm",
        "DAG": "456 ELK AVENUE",
        "DAI": "CALGARY",
        "DAJ": "AB",
        "DAK": "T2P 1J9",
        "DCG": "CAN",
        "DCA": "5",
        "DCB": "",
        "DCD": "",
        "DCF": "0000000001",
        "DDE": "N",
        "DDF": "N",
        "DDG": "N",
    }
