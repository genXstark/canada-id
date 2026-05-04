"""Comprehensive MRZ regression tests.

Covers the full pipeline end-to-end:
- All 6 Canadian document templates (generate + parse roundtrip)
- Transliteration (accented names)
- Structured validation (errors, warnings)
- Optional data roundtrip fidelity (< fillers preserved)
- Noisy input extraction (OCR garbage)
- Web UI helper functions
- Edge cases and error paths
"""
import pytest

from canada_id.mrz.canada_docs import (
    CANADIAN_DOCS,
    all_doc_types,
    doc_choices,
    get_doc_type,
)
from canada_id.mrz.checksum import compute_str, verify
from canada_id.mrz.generator import MRZData, generate_mrz
from canada_id.mrz.models import MrzFormat, MrzResult, Sex
from canada_id.mrz.parsers import MrzParseError, parse_mrz, validate_mrz
from canada_id.mrz.renderer import render_mrz_image
from canada_id.mrz.transliterate import transliterate, transliterate_name
from canada_id.mrz.utils import encode_name, lines_from_mrz, pad, unpad
from canada_id.mrz.validate import (
    MrzValidationReport,
    validate_mrz_fields,
)


# ── Canadian document template roundtrips ──


class TestAllCanadianTemplates:
    """Every Canadian document template must generate + parse cleanly."""

    @pytest.fixture(params=list(CANADIAN_DOCS.keys()))
    def doc_template(self, request):
        return CANADIAN_DOCS[request.param]

    def test_generate_correct_length(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        expected = {"TD1": 90, "TD2": 72, "TD3": 88}
        assert len(mrz) == expected[doc_template.mrz_format]

    def test_roundtrip_check_digits_valid(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        result = parse_mrz(mrz, canada_only=False)
        assert result.check_digits_valid, (
            f"{doc_template.key}: check digits invalid"
        )

    def test_roundtrip_surname_preserved(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        result = parse_mrz(mrz, canada_only=False)
        expected = transliterate_name(doc_template.sample_surname)
        assert result.surname == expected

    def test_roundtrip_doc_number_preserved(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        result = parse_mrz(mrz, canada_only=False)
        assert result.document_number == doc_template.sample_doc_num

    def test_roundtrip_nationality_preserved(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        result = parse_mrz(mrz, canada_only=False)
        assert result.nationality == doc_template.sample_nationality

    def test_roundtrip_dates_preserved(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        result = parse_mrz(mrz, canada_only=False)
        assert result.date_of_birth == doc_template.sample_dob
        assert result.expiry_date == doc_template.sample_expiry

    def test_validate_mrz_returns_true(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        assert validate_mrz(mrz, canada_only=False)

    def test_render_image_valid(self, doc_template):
        data = _data_from_template(doc_template)
        mrz = generate_mrz(data, doc_template.mrz_format)
        lines = lines_from_mrz(mrz)
        img = render_mrz_image("\n".join(lines), scale=2)
        assert img.width > 0 and img.height > 0


# ── Transliteration ──


class TestTransliteration:
    """ICAO 9303 Latin-based transliteration."""

    @pytest.mark.parametrize("input_,expected", [
        ("Côté", "COTE"),
        ("Müller", "MUELLER"),
        ("André", "ANDRE"),
        ("Hébert", "HEBERT"),
        ("Tremblay", "TREMBLAY"),
        ("Björk", "BJOERK"),
        ("Çelik", "CELIK"),
        ("Šimková", "SIMKOVA"),
        ("Straße", "STRASSE"),
        ("Ñoño", "NONO"),
    ])
    def test_transliterate_accented(self, input_, expected):
        assert transliterate(input_) == expected

    def test_transliterate_name_hyphens_to_spaces(self):
        assert transliterate_name("JEAN-PIERRE") == "JEAN PIERRE"

    def test_transliterate_name_preserves_spaces(self):
        assert transliterate_name("MAGHA MOFFO") == "MAGHA MOFFO"

    def test_encode_name_uses_transliteration(self):
        result = encode_name("Côté", "André", 30)
        assert result.startswith("COTE<<ANDRE")
        assert len(result) == 30

    def test_accented_name_roundtrip(self):
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="Côté", given_names="André",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900115", sex="M", expiry_date="340115",
        )
        mrz = generate_mrz(data, "TD3")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid
        assert result.surname == "COTE"
        assert result.given_names == "ANDRE"


# ── Structured validation ──


class TestStructuredValidation:
    """validate_mrz_fields() with field-level reporting."""

    def test_valid_fields_pass(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="SMITH", given_names="JOHN",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900115", sex="M", expiry_date="340115",
        )
        assert report.valid
        assert len(report.errors) == 0

    def test_missing_surname_error(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="", given_names="JOHN",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900115", sex="M", expiry_date="340115",
        )
        assert not report.valid
        errs = [e.field_name for e in report.errors]
        assert "Surname" in errs

    def test_doc_number_too_long(self):
        report = validate_mrz_fields(
            document_type="I", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="1234567890", nationality="CAN",
            date_of_birth="900101", sex="M", expiry_date="340101",
        )
        assert not report.valid
        errs = [e.field_name for e in report.errors]
        assert "Document Number" in errs

    def test_bad_country_code(self):
        report = validate_mrz_fields(
            document_type="P", country_code="XX",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900101", sex="M", expiry_date="340101",
        )
        assert not report.valid
        errs = [e.field_name for e in report.errors]
        assert "Issuing Country" in errs

    def test_invalid_date_format(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="13thJan", sex="M", expiry_date="340101",
        )
        assert not report.valid
        errs = [e.field_name for e in report.errors]
        assert "Date of Birth" in errs

    def test_invalid_month(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="901301", sex="M", expiry_date="340101",
        )
        assert not report.valid

    def test_invalid_sex(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900101", sex="Z", expiry_date="340101",
        )
        assert not report.valid

    def test_honorific_warning(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="DR SMITH", given_names="JOHN",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900101", sex="M", expiry_date="340101",
        )
        # Honorific is a warning, not error — still valid
        assert report.valid
        assert len(report.warnings) > 0

    def test_opt_data_too_long_td1(self):
        report = validate_mrz_fields(
            document_type="I", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900101", sex="M", expiry_date="340101",
            mrz_format="TD1",
            optional_data_1="1234567890123456",  # 16 > max 15
        )
        assert not report.valid

    def test_opt_data_too_long_td3(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900101", sex="M", expiry_date="340101",
            mrz_format="TD3",
            optional_data_1="123456789012345",  # 15 > max 14
        )
        assert not report.valid

    def test_summary_output(self):
        report = validate_mrz_fields(
            document_type="P", country_code="CAN",
            surname="SMITH", given_names="JOHN",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900115", sex="M", expiry_date="340115",
        )
        assert report.summary() == "All fields valid."


# ── Optional data roundtrip fidelity ──


class TestOptionalDataFidelity:
    """Optional data with < fillers must roundtrip exactly."""

    def test_td1_opt1_with_fillers(self):
        data = MRZData(
            document_type="I", country_code="CAN",
            surname="NABIL", given_names="FARHAN",
            document_number="PD0581563", nationality="BGD",
            date_of_birth="970102", sex="M", expiry_date="261103",
            optional_data_1="<1116288070<<<5",
        )
        mrz = generate_mrz(data, "TD1")
        result = parse_mrz(mrz, canada_only=False)
        assert result.check_digits_valid
        # Raw opt1 in the MRZ should match exactly
        assert mrz[15:30] == "<1116288070<<<5"

    def test_td1_opt2_with_fillers(self):
        data = MRZData(
            document_type="I", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900101", sex="M", expiry_date="340101",
            optional_data_1="ON<<<<<<<<<<<<<",
            optional_data_2="<210430<01<",
        )
        mrz = generate_mrz(data, "TD1")
        assert mrz[48:59] == "<210430<01<"

    def test_td1_generate_parse_regenerate_match(self):
        """Generate → parse → extract raw opt → regenerate = same."""
        data = MRZData(
            document_type="I", country_code="CAN",
            surname="NABIL", given_names="FARHAN",
            document_number="PD0581563", nationality="BGD",
            date_of_birth="970102", sex="M", expiry_date="261103",
            optional_data_1="<1116288070<<<5",
            optional_data_2="<211103<01<",
        )
        original = generate_mrz(data, "TD1")
        result = parse_mrz(original, canada_only=False)

        # Extract raw opt from raw_mrz
        opt1_raw = result.raw_mrz[15:30]
        opt2_raw = result.raw_mrz[48:59]

        data2 = MRZData(
            document_type=result.document_type,
            country_code=result.issuing_country,
            surname=result.surname,
            given_names=result.given_names,
            document_number=result.document_number,
            nationality=result.nationality,
            date_of_birth=result.date_of_birth,
            sex=result.sex.value,
            expiry_date=result.expiry_date,
            optional_data_1=opt1_raw,
            optional_data_2=opt2_raw,
        )
        regenerated = generate_mrz(data2, "TD1")
        assert original == regenerated


# ── Noisy input extraction ──


class TestNoisyInput:
    """Parser handles garbage around valid MRZ lines."""

    def test_mrz_with_ocr_header_footer(self):
        noisy = (
            "Some OCR header garbage\n"
            "I<CANPD01830178ON<<<<<<<<<<<<<\n"
            "8411279F2604309CMR<<<<<<<<<<<3\n"
            "MAGHA<MOFFO<<MATHILDE<<<<<<<<<\n"
            "footer text here"
        )
        result = parse_mrz(
            noisy, canada_only=False, auto_purify=True,
        )
        assert result.check_digits_valid
        assert result.surname == "MAGHA MOFFO"

    def test_parsed_fields_text_rejected(self):
        parsed_text = (
            "Format: TD1\n"
            "Check digits valid: True\n"
            "Document Type: I\n"
            "Country: CAN\n"
            "Surname: SMITH\n"
        )
        with pytest.raises(MrzParseError):
            parse_mrz(parsed_text, canada_only=False)

    def test_wrong_length_clear_error(self):
        with pytest.raises(MrzParseError, match="raw MRZ lines"):
            parse_mrz("A" * 50, canada_only=False)

    def test_newlines_stripped_correctly(self):
        mrz_lines = (
            "P<CANTREMBLAY<<MARIE<CLAIRE"
            "<<<<<<<<<<<<<<<<<\n"
            "AB12345671CAN8503208F3403208"
            "<<<<<<<<<<<<<<00"
        )
        result = parse_mrz(mrz_lines, canada_only=False)
        assert result.format == MrzFormat.TD3

    def test_auto_purify_strips_invalid_chars(self):
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="SMITH", given_names="JOHN",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900115", sex="M", expiry_date="340115",
        )
        clean = generate_mrz(data, "TD3")
        # Insert some invalid chars
        dirty = clean[:10] + "!@#" + clean[10:]
        result = parse_mrz(dirty, canada_only=False, auto_purify=True)
        assert result.check_digits_valid


# ── Canada docs registry ──


class TestCanadaDocs:
    """Canadian document type definitions."""

    def test_six_doc_types_registered(self):
        assert len(CANADIAN_DOCS) == 6

    def test_all_keys_present(self):
        expected = {
            "passport", "pr_card", "edl",
            "nexus", "refugee_travel", "emergency_travel",
        }
        assert set(CANADIAN_DOCS.keys()) == expected

    def test_get_doc_type(self):
        doc = get_doc_type("passport")
        assert doc.name == "Passport"
        assert doc.mrz_format == "TD3"

    def test_get_doc_type_missing_raises(self):
        with pytest.raises(KeyError):
            get_doc_type("nonexistent")

    def test_doc_choices_format(self):
        choices = doc_choices()
        assert len(choices) == 6
        assert all(" - " in c for c in choices)

    def test_all_doc_types_list(self):
        docs = all_doc_types()
        assert len(docs) == 6

    def test_passport_is_td3(self):
        assert get_doc_type("passport").mrz_format == "TD3"

    def test_pr_card_is_td1(self):
        assert get_doc_type("pr_card").mrz_format == "TD1"

    def test_pr_card_nationality_not_can(self):
        doc = get_doc_type("pr_card")
        assert doc.sample_nationality != "CAN"


# ── Web UI helpers ──


class TestWebUIHelpers:
    """Web UI functions that don't need Gradio running."""

    def test_clean_mrz_field(self):
        from canada_id.web import _clean_mrz_field
        assert _clean_mrz_field("AB 123", "test") == "AB123"
        assert _clean_mrz_field("  CAN  ", "test") == "CAN"
        assert _clean_mrz_field("abc!@#", "test") == "ABC"
        assert _clean_mrz_field("", "test") == ""
        assert _clean_mrz_field(None, "test") == ""

    def test_barcode_size_ontario(self):
        from canada_id.web import _barcode_size
        assert _barcode_size("ON") == (805, 116)

    def test_barcode_size_default(self):
        from canada_id.web import _barcode_size
        # AAMVA-default territories
        assert _barcode_size("PE") == (404, 82)
        assert _barcode_size("YT") == (404, 82)
        # Provinces with custom sizes
        assert _barcode_size("BC") == (640, 130)
        assert _barcode_size("AB") == (565, 110)
        # Unknown code falls back to default
        assert _barcode_size("ZZ") == (404, 82)

    def test_doc_type_choices(self):
        from canada_id.web import _doc_type_choices
        choices = _doc_type_choices()
        assert len(choices) == 6

    def test_load_doc_template_passport(self):
        from canada_id.web import _load_doc_template
        result = _load_doc_template("passport - Passport")
        assert result[0] == "P"       # doc_type
        assert result[1] == "TD3"     # format
        assert result[2] == "CAN"     # country

    def test_load_doc_template_pr_card(self):
        from canada_id.web import _load_doc_template
        result = _load_doc_template("pr_card - Permanent Resident Card")
        # Real Canadian PR cards use 'CA' as doc type, not 'I<'
        assert result[0] == "CA"      # doc_type per real PR card
        assert result[1] == "TD1"     # format
        assert result[6] == "CMR"     # nationality (not CAN)

    def test_load_doc_template_empty(self):
        from canada_id.web import _load_doc_template
        result = _load_doc_template("")
        assert result[0] == "I"       # default doc_type

    def test_mrz_generate_valid(self):
        from canada_id.web import _mrz_generate
        display, img, status = _mrz_generate(
            "P", "TD3", "CAN", "SMITH", "JOHN",
            "AB1234567", "CAN", "900115", "M", "340115", "", "",
        )
        assert "OK" in status
        assert "VALID" in status
        assert img is not None
        assert len(display.replace("\n", "")) == 88

    def test_mrz_generate_validation_error(self):
        from canada_id.web import _mrz_generate
        display, img, status = _mrz_generate(
            "P", "TD3", "CAN", "", "JOHN",
            "AB1234567", "CAN", "900115", "M", "340115", "", "",
        )
        assert img is None
        assert "Surname" in status

    def test_mrz_parse_text(self):
        from canada_id.web import _mrz_parse_text
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="SMITH", given_names="JOHN",
            document_number="AB1234567", nationality="CAN",
            date_of_birth="900115", sex="M", expiry_date="340115",
        )
        mrz = generate_mrz(data, "TD3")
        lines = lines_from_mrz(mrz)
        parsed, status = _mrz_parse_text("\n".join(lines), True)
        assert "VALID" in status
        assert "SMITH" in parsed

    def test_mrz_compare_match(self):
        from canada_id.web import _mrz_compare
        mrz = "I<CANTEST<<<<<<<<<<<<<<<<<<<<<<"
        result = _mrz_compare(mrz, mrz)
        assert "MATCH" in result

    def test_mrz_compare_mismatch(self):
        from canada_id.web import _mrz_compare
        result = _mrz_compare("AAAA", "BBBB")
        assert "MISMATCH" in result


# ── Edge cases ──


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_max_length_doc_number(self):
        data = MRZData(
            document_type="I", country_code="CAN",
            surname="X", given_names="Y",
            document_number="ABCDE6789",  # exactly 9
            nationality="CAN",
            date_of_birth="000101", sex="M", expiry_date="340101",
        )
        mrz = generate_mrz(data, "TD1")
        result = parse_mrz(mrz, canada_only=True)
        assert result.document_number == "ABCDE6789"

    def test_single_char_name(self):
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="X", given_names="Y",
            document_number="A12345678", nationality="CAN",
            date_of_birth="000101", sex="X", expiry_date="340101",
        )
        mrz = generate_mrz(data, "TD3")
        result = parse_mrz(mrz, canada_only=True)
        assert result.surname == "X"
        assert result.sex == Sex.UNSPECIFIED

    def test_sex_x_roundtrip(self):
        data = MRZData(
            document_type="P", country_code="CAN",
            surname="NONBINARY", given_names="PERSON",
            document_number="NB1234567", nationality="CAN",
            date_of_birth="950601", sex="X", expiry_date="350601",
        )
        mrz = generate_mrz(data, "TD3")
        result = parse_mrz(mrz, canada_only=True)
        assert result.sex == Sex.UNSPECIFIED

    def test_empty_optional_data(self):
        data = MRZData(
            document_type="I", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="A12345678", nationality="CAN",
            date_of_birth="000101", sex="M", expiry_date="340101",
        )
        mrz = generate_mrz(data, "TD1")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid

    def test_full_optional_data_td1(self):
        data = MRZData(
            document_type="I", country_code="CAN",
            surname="TEST", given_names="USER",
            document_number="A12345678", nationality="CAN",
            date_of_birth="000101", sex="M", expiry_date="340101",
            optional_data_1="ABCDE1234567890",  # exactly 15
            optional_data_2="12345678901",       # exactly 11
        )
        mrz = generate_mrz(data, "TD1")
        result = parse_mrz(mrz, canada_only=True)
        assert result.check_digits_valid

    def test_lines_from_mrz_td1(self):
        assert len(lines_from_mrz("A" * 90)) == 3

    def test_lines_from_mrz_td2(self):
        assert len(lines_from_mrz("A" * 72)) == 2

    def test_lines_from_mrz_td3(self):
        assert len(lines_from_mrz("A" * 88)) == 2

    def test_lines_from_mrz_with_newlines(self):
        lines = lines_from_mrz("AAA\nBBB\nCCC")
        assert len(lines) == 3

    def test_pad_and_unpad(self):
        assert pad("AB", 5) == "AB<<<"
        assert pad("ABCDE", 3) == "ABC"
        assert unpad("AB<<<") == "AB"
        assert unpad("<<<") == ""


# ── Helper ──


def _data_from_template(doc):
    """Create MRZData from a CanadianDocType template."""
    return MRZData(
        document_type=doc.document_type,
        country_code=doc.issuing_country,
        surname=doc.sample_surname,
        given_names=doc.sample_given,
        document_number=doc.sample_doc_num,
        nationality=doc.sample_nationality,
        date_of_birth=doc.sample_dob,
        sex=doc.sample_sex,
        expiry_date=doc.sample_expiry,
        optional_data_1=doc.sample_opt1,
        optional_data_2=doc.sample_opt2,
    )
