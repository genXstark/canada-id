"""Gradio web UI for canada-id barcode encoding and decoding."""
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib import error, request

import gradio as gr
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from canada_id.ai_config import provider_status_markdown
from canada_id.guards import auto_fix_province, check_province_match
from canada_id.mrz_guide import get_mrz_guide_html
from canada_id.provinces.registry import all_profiles, get_profile
from canada_id.sample_store import PRSampleStore
from canada_id.storage import HistoryDB

_db = HistoryDB()
_pr_store = PRSampleStore()

_BUILTIN_PR_SAMPLES: dict[str, dict[str, str]] = {
    "builtin:PR Basic Canada": {
        "document_type": "I",
        "country_code": "CAN",
        "document_number": "R12345678",
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "nationality": "CAN",
        "date_of_birth": "950523",
        "sex": "M",
        "expiry_date": "290523",
        "country_of_birth": "CANADA",
        "pr_number": "123456789",
        "optional_data_1": "PR1234567",
    },
    "builtin:PR Female Example": {
        "document_type": "I",
        "country_code": "CAN",
        "document_number": "R87654321",
        "surname": "TREMBLAY",
        "given_names": "MARIE CLAIRE",
        "nationality": "CAN",
        "date_of_birth": "900215",
        "sex": "F",
        "expiry_date": "300215",
        "country_of_birth": "CANADA",
        "pr_number": "987654321",
        "optional_data_1": "PR9876543",
    },
}


@dataclass(frozen=True)
class EditPlan:
    """Simple image enhancement plan."""

    brightness: float
    contrast: float
    color: float
    sharpness: float


def _province_choices() -> list[str]:
    """Build province dropdown choices."""
    return [f"{p.code} - {p.name}" for p in all_profiles()]


def _extract_code(choice: str) -> str:
    """Extract province code from dropdown choice string."""
    return choice.split(" - ")[0].strip().upper() if choice else ""


# Province-specific PDF417 barcode dimensions (width, height) in pixels.
# Sizes derived from public spec sheets and AAMVA test card observations.
# Provinces marked "default" use the AAMVA reference 404x82.
_BARCODE_SIZES: dict[str, tuple[int, int]] = {
    "ON": (805, 116),  # Confirmed: Ontario DL/photocard wider format
    "BC": (640, 130),  # BC Services Card / DL standard
    "AB": (565, 110),  # Alberta DL standard
    "QC": (605, 130),  # Quebec permis de conduire standard
    "MB": (485, 95),   # Manitoba DL standard
    "SK": (485, 95),   # Saskatchewan DL standard
    "NS": (450, 90),   # Nova Scotia DL standard
    "NB": (450, 90),   # New Brunswick DL standard
    "NL": (450, 90),   # Newfoundland DL standard
    "PE": (404, 82),   # Prince Edward Island - AAMVA default
    "NT": (404, 82),   # Northwest Territories - AAMVA default
    "NU": (404, 82),   # Nunavut - AAMVA default
    "YT": (404, 82),   # Yukon - AAMVA default
}
_DEFAULT_BARCODE_SIZE = (404, 82)


def _barcode_size(province_code: str) -> tuple[int, int]:
    """Return barcode pixel dimensions for a province."""
    return _BARCODE_SIZES.get(province_code, _DEFAULT_BARCODE_SIZE)


def _decode_image(image):
    """Decode a PDF417 barcode image and parse AAMVA fields."""
    if image is None:
        return "No image provided.", "", ""

    from canada_id.aamva.parser import parse_aamva
    from canada_id.codec.decoder import decode_pdf417_text

    pil_image = Image.fromarray(image)
    payloads = decode_pdf417_text(pil_image)

    if not payloads:
        return "No PDF417 barcode found.", "", ""

    raw = payloads[0]
    fields = parse_aamva(raw)
    table = "\n".join(f"{k}: {v}" for k, v in sorted(fields.items()))

    # Auto-detect province from decoded data
    detected, reason = auto_fix_province(fields)
    province_info = f"Province: {detected} ({reason})" if detected else reason

    # Log to history
    _db.log_decode(
        fields=fields,
        raw_payload=raw,
        province=detected,
        source_img=pil_image,
    )

    return table, raw, province_info


def _encode_barcode(province_choice, fields_json):
    """Generate a PDF417 barcode from AAMVA field data."""
    if not province_choice or not fields_json:
        return None, "Please select a province and enter field data.", ""

    from canada_id.aamva.builder import build_aamva
    from canada_id.codec.encoder import barcode_to_image, encode_pdf417

    province_code = _extract_code(province_choice)

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}", ""

    # Province mismatch guard — auto-corrects instead of blocking
    status_msg = ""
    mismatches = check_province_match(province_code, fields)
    if mismatches:
        detected, reason = auto_fix_province(fields)
        if detected:
            province_code = detected
            status_msg = (
                f"AUTO-CORRECTED: You selected {_extract_code(province_choice)}"
                f" but your data is for {detected}."
                f" Generated with {detected} instead."
            )
        else:
            status_msg = "WARNING: " + "; ".join(m.message for m in mismatches)

    aamva_string = build_aamva(fields, province_code)
    barcode = encode_pdf417(aamva_string)
    img = barcode_to_image(barcode, scale=3)
    w, h = _barcode_size(province_code)
    img = img.resize((w, h), Image.NEAREST)

    if not status_msg:
        status_msg = f"OK — generated for {province_code}"

    # Log to history
    _db.log_encode(
        province=province_code,
        fields=fields,
        aamva_string=aamva_string,
        barcode_img=img,
    )

    return img, aamva_string, status_msg


def _validate_fields(province_choice, fields_json):
    """Validate AAMVA fields against province rules."""
    if not province_choice or not fields_json:
        return "Please select a province and enter field data."

    from canada_id.aamva.validator import validate_aamva

    province_code = _extract_code(province_choice)

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    # Province mismatch check first
    mismatches = check_province_match(province_code, fields)
    lines = []
    if mismatches:
        for m in mismatches:
            tag = "MISMATCH" if m.severity == "error" else "WARNING"
            lines.append(f"[{tag}] {m.field}: {m.message}")
        lines.append("")

    errors = validate_aamva(fields, province_code)
    if not errors and not mismatches:
        result = "All fields valid."
    else:
        for err in errors:
            icon = "ERROR" if err.severity == "error" else "WARN"
            lines.append(f"[{icon}] {err.field}: {err.message}")
        result = "\n".join(lines) if lines else "All fields valid."

    # Log validation
    error_strs = [f"{e.field}: {e.message}" for e in errors]
    _db.log_validate(province_code, fields, error_strs)

    return result


def _auto_detect_province(fields_json):
    """Auto-detect province from field data and return dropdown value."""
    if not fields_json:
        return gr.update(), "Enter field data first."

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError:
        return gr.update(), "Invalid JSON."

    detected, reason = auto_fix_province(fields)
    if detected:
        try:
            profile = get_profile(detected)
            choice = f"{profile.code} - {profile.name}"
            return gr.update(value=choice), reason
        except KeyError:
            return gr.update(), f"Unknown province code: {detected}"

    return gr.update(), reason


def _sample_fields():
    """Return sample AAMVA field JSON for Ontario."""
    sample = {
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
    return json.dumps(sample, indent=2)


def _get_history_table(op_filter, province_filter):
    """Fetch history as a table for display."""
    op_type = op_filter if op_filter and op_filter != "all" else None
    province = province_filter if province_filter else None

    records = _db.get_history(op_type=op_type, province=province, limit=50)
    rows = []
    for r in records:
        fields_preview = ""
        if r.fields:
            name = r.fields.get("DAC", "") + " " + r.fields.get("DCS", "")
            name = name.strip()
            dl = r.fields.get("DAQ", "")
            fields_preview = f"{name} | {dl}" if name else dl

        rows.append([
            r.id,
            r.created_at_iso,
            r.op_type.upper(),
            r.province or "—",
            fields_preview,
            "Yes" if r.errors else "No",
        ])

    return rows


def _generate_code39(text):
    """Generate a Code 39 barcode image from text."""
    if not text or not text.strip():
        return None, "Enter text to encode."

    from canada_id.codec.code39 import code39_to_image

    try:
        img = code39_to_image(text.strip())
        return img, f"OK — encoded '{text.strip()}' as Code 39"
    except ValueError as e:
        return None, f"Invalid input: {e}"


def _composite_card(card_image, barcode_image, x_frac, y_frac,
                    w_frac, h_frac, rotation):
    """Composite a barcode onto a card template."""
    if card_image is None:
        return None, "Upload a card template image."
    if barcode_image is None:
        return None, "Upload or generate a barcode image first."

    from canada_id.card.compositor import composite_barcode_on_card
    from canada_id.card.layout import BarcodeRegion

    card = Image.fromarray(card_image)
    barcode = Image.fromarray(barcode_image)

    region = BarcodeRegion(
        x_frac=float(x_frac),
        y_frac=float(y_frac),
        w_frac=float(w_frac),
        h_frac=float(h_frac),
        rotation_deg=float(rotation),
    )

    result = composite_barcode_on_card(card, barcode, region)
    status = (
        f"OK — composited at ({x_frac}, {y_frac})"
        f" size ({w_frac}x{h_frac}) rotation {rotation} deg"
    )
    return result, status


def _mrz_result_text(result) -> str:
    """Format an MrzResult into readable text.

    Includes raw optional data extracted directly from the
    MRZ string to preserve exact encoding (with < fillers).
    """
    from canada_id.mrz.models import MrzFormat

    lines = [
        f"Format: {result.format.value}",
        f"Check digits valid: {result.check_digits_valid}",
        f"Document Type: {result.document_type}",
        f"Country: {result.issuing_country}",
        f"Surname: {result.surname}",
        f"Given Names: {result.given_names}",
        f"Document Number: {result.document_number}",
        f"Nationality: {result.nationality}",
        f"DOB: {result.date_of_birth}",
        f"Sex: {result.sex.value}",
        f"Expiry: {result.expiry_date}",
    ]

    # Extract raw optional data from raw_mrz to preserve
    # exact < filler positions (needed for roundtrip)
    raw_opt1, raw_opt2 = _extract_raw_optional(result)

    if raw_opt1:
        lines.append(f"Optional 1: {raw_opt1}")
    if raw_opt2:
        lines.append(f"Optional 2: {raw_opt2}")
    if result.personal_number:
        pn = _extract_raw_personal_number(result)
        lines.append(f"Personal Number: {pn}")
    if result.birth_date:
        lines.append(f"Birth Date: {result.birth_date.isoformat()}")
    if result.expiry_date_parsed:
        lines.append(
            f"Expiry Date: {result.expiry_date_parsed.isoformat()}"
        )
    return "\n".join(lines)


def _extract_raw_optional(result) -> tuple[str, str]:
    """Extract raw optional data from raw_mrz preserving <."""
    from canada_id.mrz.models import MrzFormat

    raw = result.raw_mrz
    if not raw:
        return result.optional_data_1, result.optional_data_2

    if result.format == MrzFormat.TD1 and len(raw) == 90:
        opt1 = raw[15:30]   # line 1, positions 16-30
        opt2 = raw[48:59]   # line 2, positions 19-29
        return opt1, opt2
    if result.format == MrzFormat.TD2 and len(raw) == 72:
        opt1 = raw[65:72]   # line 2, positions 30-36
        return opt1, ""
    return result.optional_data_1, result.optional_data_2


def _extract_raw_personal_number(result) -> str:
    """Extract raw personal number from raw_mrz preserving <."""
    from canada_id.mrz.models import MrzFormat

    raw = result.raw_mrz
    if result.format == MrzFormat.TD3 and len(raw) == 88:
        return raw[72:86]   # line 2, positions 29-42
    return result.personal_number


def _doc_type_choices() -> list[str]:
    """Build document type dropdown choices."""
    from canada_id.mrz.canada_docs import doc_choices
    return doc_choices()


def _show_doc_info(doc_choice: str) -> str:
    """Show educational info for selected doc type: eras, chip, doc# format."""
    from canada_id.mrz.canada_docs import CANADIAN_DOCS

    if not doc_choice:
        return (
            "Select a template to see card era, chip type, and"
            " document number format details."
        )
    key = doc_choice.split(" - ")[0].strip()
    doc = CANADIAN_DOCS.get(key)
    if not doc:
        return "Unknown template."

    lines = [f"**{doc.name}** ({doc.mrz_format}, {doc.issuing_country})"]
    if doc.card_eras:
        lines.append("")
        lines.append("**Card eras:**")
        for era, note in doc.card_eras:
            lines.append(f"- *{era}* — {note}")
    if doc.chip_type:
        lines.append("")
        lines.append(f"**Chip:** {doc.chip_type}")
    if doc.doc_number_formats:
        lines.append("")
        lines.append("**Doc number formats accepted:**")
        for fmt in doc.doc_number_formats:
            lines.append(f"- `{fmt}`")
    if doc.has_pdf417:
        lines.append("")
        lines.append("**Barcode:** Has PDF417")
    elif doc.mrz_format == "TD1":
        lines.append("")
        lines.append("**Barcode:** None (post-2015 PR cards)")
    if doc.nationality_note:
        lines.append("")
        lines.append(f"**Nationality:** {doc.nationality_note}")
    return "\n".join(lines)


def _load_doc_template(doc_choice: str):
    """Load sample fields for a Canadian document type."""
    from canada_id.mrz.canada_docs import CANADIAN_DOCS

    if not doc_choice:
        return (
            "I", "TD1", "CAN", "", "", "",
            "CAN", "", "M", "", "", "",
        )

    key = doc_choice.split(" - ")[0].strip()
    doc = CANADIAN_DOCS.get(key)
    if not doc:
        return (
            "I", "TD1", "CAN", "", "", "",
            "CAN", "", "M", "", "", "",
        )

    return (
        doc.document_type,
        doc.mrz_format,
        doc.issuing_country,
        doc.sample_surname,
        doc.sample_given,
        doc.sample_doc_num,
        doc.sample_nationality,
        doc.sample_dob,
        doc.sample_sex,
        doc.sample_expiry,
        doc.sample_opt1,
        doc.sample_opt2,
    )


def _clean_mrz_field(value: str, field_name: str) -> str:
    """Strip spaces and invalid chars from an MRZ input field."""
    if not value:
        return ""
    cleaned = value.strip().replace(" ", "")
    # Remove any non-MRZ characters
    import re
    cleaned = re.sub(r"[^A-Za-z0-9<]", "", cleaned)
    return cleaned.upper()


def _mrz_load_from_json(json_text: str):
    """Parse JSON payload and return MRZ form field tuple.

    Accepts the same field names as the example payload, e.g.:
      {
        "Document Type": "P",
        "MRZ Format": "TD3",
        "Issuing Country": "CAN",
        "Document Number": "AB123456",
        "Surname": "RAHMAN",
        "Given Names": "BADR",
        "Nationality": "CAN",
        "Sex": "M",
        "Date of Birth": "970614",
        "Expiry Date": "280701",
        "Optional Data 1": "",
        "Issuing Authority": "GATINEAU"   # ignored, not in MRZ
      }
    Status output notes any extraneous keys (like Issuing Authority).
    """
    if not json_text or not json_text.strip():
        return (
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            "Paste a JSON payload first.",
        )
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return (
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            f"Invalid JSON: {e}",
        )

    # Map JSON keys to form fields (accept multiple casings)
    def g(*keys, default=""):
        for k in keys:
            if k in data:
                return str(data[k])
        return default

    doc_type = g("Document Type", "document_type", default="I")
    mrz_format = g("MRZ Format", "mrz_format", default="TD1")
    country = g("Issuing Country", "country_code", "country", default="CAN")
    surname = g("Surname", "surname")
    given = g("Given Names", "given_names", "given")
    doc_num = g("Document Number", "document_number", "doc_num")
    nationality = g("Nationality", "nationality", default="CAN")
    dob = g("Date of Birth", "date_of_birth", "dob")
    sex = g("Sex", "sex", default="M")
    expiry = g("Expiry Date", "expiry_date", "expiry")
    opt1 = g("Optional Data 1", "optional_data_1", "opt1")
    opt2 = g("Optional Data 2", "optional_data_2", "opt2")

    # Detect non-MRZ fields and warn
    non_mrz_keys = [
        k for k in data
        if k in ("Issuing Authority", "issuing_authority",
                 "Place of Birth", "place_of_birth",
                 "Photo", "photo", "Signature", "signature")
    ]
    note = ""
    if non_mrz_keys:
        note = (
            f" Note: ignored non-MRZ field(s): {', '.join(non_mrz_keys)}"
            f" (printed on document but not in MRZ)."
        )
    return (
        doc_type[:1].upper() if doc_type else "I",
        mrz_format.upper() if mrz_format else "TD1",
        country.upper(),
        surname.upper(),
        given.upper(),
        doc_num.upper(),
        nationality.upper(),
        dob,
        sex.upper()[:1] if sex else "M",
        expiry,
        opt1,
        opt2,
        f"Loaded {surname.upper()}, {given.upper()}.{note}",
    )


def _mrz_generate(
    doc_type, mrz_format, country, surname, given_names,
    doc_num, nationality, dob, sex, expiry, opt1, opt2,
):
    """Generate MRZ from form fields with structured validation."""
    from canada_id.mrz.generator import MRZData, generate_mrz
    from canada_id.mrz.renderer import render_mrz_image
    from canada_id.mrz.utils import lines_from_mrz
    from canada_id.mrz.validate import validate_mrz_fields

    # Clean all fields — strip spaces, invalid chars
    doc_type = (doc_type or "I").strip()
    mrz_format = (mrz_format or "TD1").strip()
    country = _clean_mrz_field(country, "Country")
    surname_clean = (surname or "").strip()
    given_clean = (given_names or "").strip()
    doc_num = _clean_mrz_field(doc_num, "Document Number")
    nationality = _clean_mrz_field(nationality, "Nationality")
    dob = _clean_mrz_field(dob, "Date of Birth")
    sex = (sex or "M").strip()
    expiry = _clean_mrz_field(expiry, "Expiry Date")
    opt1 = _clean_mrz_field(opt1, "Optional Data 1")
    opt2 = _clean_mrz_field(opt2, "Optional Data 2")

    # Structured validation with clear field-level messages
    report = validate_mrz_fields(
        document_type=doc_type,
        country_code=country,
        surname=surname_clean,
        given_names=given_clean,
        document_number=doc_num,
        nationality=nationality,
        date_of_birth=dob,
        sex=sex,
        expiry_date=expiry,
        mrz_format=mrz_format,
        optional_data_1=opt1,
        optional_data_2=opt2,
    )

    if not report.valid:
        return "", None, report.summary()

    # Warnings are OK — show them alongside success
    warn_text = ""
    if report.warnings:
        warn_text = "\n" + "\n".join(
            f"⚠ {w.field_name}: {w.message}"
            for w in report.warnings
        )

    try:
        data = MRZData(
            document_type=doc_type,
            country_code=country,
            surname=surname_clean,
            given_names=given_clean,
            document_number=doc_num,
            nationality=nationality,
            date_of_birth=dob,
            sex=sex,
            expiry_date=expiry,
            optional_data_1=opt1,
            optional_data_2=opt2,
        )
        mrz = generate_mrz(data, mrz_format)
        lines = lines_from_mrz(mrz)
        display = "\n".join(lines)
        img = render_mrz_image(display, scale=3)

        # Roundtrip validation — parse what we generated
        from canada_id.mrz.parsers import parse_mrz
        try:
            result = parse_mrz(
                mrz, canada_only=False,
            )
            if result.check_digits_valid:
                status = f"OK - {mrz_format} generated, check digits VALID"
            else:
                status = (
                    f"OK - {mrz_format} generated"
                    f" but check digits INVALID"
                )
        except Exception:
            status = f"OK - {mrz_format} generated"

        if warn_text:
            status += warn_text
        return display, img, status
    except (ValueError, Exception) as e:
        return "", None, f"Error: {e}"


def _mrz_scan_image(image):
    """Extract MRZ from uploaded document image via OCR."""
    if image is None:
        return "", "", "Upload a passport or PR card image."

    from canada_id.mrz.ocr_reader import extract_mrz_from_image
    from canada_id.mrz.parsers import MrzParseError, parse_mrz
    from canada_id.mrz.utils import lines_from_mrz

    pil_image = Image.fromarray(image)
    mrz_text = extract_mrz_from_image(pil_image)

    if not mrz_text:
        return "", "", (
            "Could not extract MRZ from image."
            " Try a clearer photo or paste the MRZ"
            " text manually below."
        )

    lines = lines_from_mrz(mrz_text)
    display = "\n".join(lines)

    try:
        result = parse_mrz(
            mrz_text, ocr_correct=True, canada_only=False,
            auto_purify=True,
        )
        parsed = _mrz_result_text(result)
        valid = "VALID" if result.check_digits_valid else "INVALID"
        status = f"Extracted and parsed. Check digits: {valid}"
        return display, parsed, status
    except MrzParseError as e:
        # Best-effort fallback: extract what we can so the user
        # can still click Fill from Scan and fix manually
        parsed = _best_effort_extract(mrz_text)
        status = (
            f"Parse failed ({e}). Showing best-effort fields"
            f" — edit and re-parse or click Fill from Scan."
        )
        return display, parsed, status
    except ValueError as e:
        parsed = _best_effort_extract(mrz_text)
        return display, parsed, f"Validation failed: {e}"


def _best_effort_extract(mrz_text: str) -> str:
    """Extract whatever fields we can from corrupted MRZ text.

    Uses landmark scanning (sex marker, known positions) rather
    than strict regex. Always returns parseable field text for
    Fill from Scan to consume.
    """
    from canada_id.mrz.utils import lines_from_mrz, split_names

    lines = lines_from_mrz(mrz_text)
    if not lines:
        return ""

    fields = {
        "Format": "TD3" if len(lines) == 2 else "TD1",
        "Check digits valid": "False",
        "Document Type": "P" if len(lines) == 2 else "I",
        "Country": "CAN",
        "Surname": "",
        "Given Names": "",
        "Document Number": "",
        "Nationality": "CAN",
        "DOB": "",
        "Sex": "M",
        "Expiry": "",
        "Optional 1": "",
        "Optional 2": "",
    }

    line1 = lines[0] if lines else ""
    line2 = lines[1] if len(lines) > 1 else ""
    line3 = lines[2] if len(lines) > 2 else ""

    # Line 1: doc type + country + name field
    if len(line1) >= 5:
        fields["Document Type"] = line1[0] if line1[0] in "PIAC" else "P"
        fields["Country"] = line1[2:5]

    # Name field: differs by format
    if len(lines) == 2 and len(line1) >= 44:
        # TD3: name in line 1 positions 5-44
        name_field = line1[5:44]
        surname, given = split_names(name_field)
        fields["Surname"] = surname or ""
        fields["Given Names"] = given or ""
    elif len(lines) == 3 and len(line3) >= 30:
        # TD1: name in line 3
        surname, given = split_names(line3)
        fields["Surname"] = surname or ""
        fields["Given Names"] = given or ""

    # Line 2: data fields — use sex marker as anchor
    if line2:
        sex_idx = -1
        for i, ch in enumerate(line2):
            if ch in "MFX" and 15 <= i <= 25:
                sex_idx = i
                break
        if sex_idx > 0:
            fields["Sex"] = line2[sex_idx]
            # Dates relative to sex position
            if sex_idx >= 7:
                # dob is 7 chars before sex (6 digits + 1 check)
                dob_raw = line2[sex_idx - 7:sex_idx - 1]
                fields["DOB"] = dob_raw
            if sex_idx + 7 <= len(line2):
                expiry_raw = line2[sex_idx + 1:sex_idx + 7]
                fields["Expiry"] = expiry_raw
            # Doc number is first 9 chars of line 2
            fields["Document Number"] = line2[:9].replace("<", "")
            # Nationality is typically 3 chars before dob
            if sex_idx >= 10:
                fields["Nationality"] = line2[sex_idx - 10:sex_idx - 7]

    return "\n".join(f"{k}: {v}" for k, v in fields.items() if v)


def _mrz_fill_from_scan(scan_parsed):
    """Fill generate form from scanned/parsed MRZ fields.

    Optional data fields preserve < characters from the
    raw MRZ to ensure roundtrip fidelity (same check digits).
    """
    if not scan_parsed or not scan_parsed.strip():
        return (
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(),
            "Scan a document first.",
        )

    fields = {}
    for line in scan_parsed.strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fields[key.strip()] = val.strip()

    fmt = fields.get("Format", "TD1")
    doc_type = fields.get("Document Type", "I")
    country = fields.get("Country", "CAN")
    surname = fields.get("Surname", "")
    given = fields.get("Given Names", "")
    doc_num = fields.get("Document Number", "")
    nationality = fields.get("Nationality", "CAN")
    dob = fields.get("DOB", "")
    sex = fields.get("Sex", "M")
    expiry = fields.get("Expiry", "")
    opt1 = fields.get("Optional 1", "")
    if not opt1:
        opt1 = fields.get("Personal Number", "")
    opt2 = fields.get("Optional 2", "")

    # Map doc type character
    if doc_type and len(doc_type) >= 1:
        doc_type = doc_type[0]

    # Clean code/date fields — remove spaces and invalid chars
    doc_num = _clean_mrz_field(doc_num, "doc_num")
    country = _clean_mrz_field(country, "country")
    nationality = _clean_mrz_field(nationality, "nationality")
    dob = _clean_mrz_field(dob, "dob")
    expiry = _clean_mrz_field(expiry, "expiry")

    # Optional data: preserve < fillers for exact roundtrip.
    # These come from raw MRZ extraction with < intact.
    opt1 = opt1.strip().upper()
    opt2 = opt2.strip().upper()

    return (
        doc_type, fmt, country,
        surname, given, doc_num, nationality,
        dob, sex, expiry, opt1, opt2,
        f"Filled from scan: {surname}, {given}",
    )


def _mrz_parse_text(mrz_text, ocr_correct):
    """Parse manually entered MRZ text."""
    from canada_id.mrz.parsers import MrzParseError, parse_mrz

    if not mrz_text or not mrz_text.strip():
        return "", "Enter or paste MRZ text."

    try:
        result = parse_mrz(
            mrz_text.strip(),
            ocr_correct=bool(ocr_correct),
            canada_only=False,
            auto_purify=True,
        )
        parsed = _mrz_result_text(result)
        valid = "VALID" if result.check_digits_valid else "INVALID"
        return parsed, f"Check digits: {valid}"
    except MrzParseError as e:
        parsed = _best_effort_extract(mrz_text.strip())
        return parsed, (
            f"Parse failed ({e}). Showing best-effort fields"
            f" — click Fill from Paste to use them."
        )
    except ValueError as e:
        parsed = _best_effort_extract(mrz_text.strip())
        return parsed, f"Validation failed: {e}"


def _mrz_export_txt(generated, parsed, status):
    """Export MRZ results as plain text."""
    lines = ["=== MRZ Export ===", ""]
    if generated:
        lines.append("GENERATED MRZ:")
        lines.append(generated)
        lines.append("")
    if parsed:
        lines.append("PARSED FIELDS:")
        lines.append(parsed)
        lines.append("")
    if status:
        lines.append(f"STATUS: {status}")
    if not generated and not parsed:
        return "Nothing to export. Generate or scan first."
    return "\n".join(lines)


def _mrz_export_json(generated, parsed, status):
    """Export MRZ results as JSON."""
    data = {}
    if generated:
        data["mrz_raw"] = generated.replace("\n", "")
        data["mrz_lines"] = generated.strip().split("\n")
    if parsed:
        fields = {}
        for line in parsed.strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                fields[key.strip()] = val.strip()
        data["fields"] = fields
    if status:
        data["status"] = status
    if not data:
        return '{"error": "Nothing to export"}'
    return json.dumps(data, indent=2)


def _mrz_compare(generated_mrz, scanned_mrz):
    """Compare generated MRZ against scanned MRZ."""
    if not generated_mrz or not scanned_mrz:
        return "Generate an MRZ and scan a document first."

    gen = generated_mrz.replace("\n", "").replace(" ", "")
    scan = scanned_mrz.replace("\n", "").replace(" ", "")

    if gen == scan:
        return "MATCH - Generated MRZ matches scanned MRZ exactly."

    lines = ["MISMATCH - Differences found:", ""]
    if len(gen) != len(scan):
        lines.append(
            f"Length: generated={len(gen)}, scanned={len(scan)}"
        )

    min_len = min(len(gen), len(scan))
    diffs = []
    for i in range(min_len):
        if gen[i] != scan[i]:
            diffs.append(f"  Position {i}: generated='{gen[i]}'"
                         f" scanned='{scan[i]}'")
    if diffs:
        lines.append(f"Character differences ({len(diffs)}):")
        lines.extend(diffs[:20])
        if len(diffs) > 20:
            lines.append(f"  ... and {len(diffs) - 20} more")

    return "\n".join(lines)


def _default_pr_fields() -> str:
    """Return starter fields for a PR card."""
    sample = {
        "document_type": "I",
        "country_code": "CAN",
        "document_number": "R12345678",
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "nationality": "CAN",
        "date_of_birth": "950523",
        "sex": "M",
        "expiry_date": "290523",
        "country_of_birth": "CANADA",
        "pr_number": "123456789",
        "optional_data_1": "PR1234567",
    }
    return json.dumps(sample, indent=2)


def _default_passport_fields() -> str:
    """Return starter fields for a passport."""
    sample = {
        "document_type": "P",
        "country_code": "CAN",
        "document_number": "AB1234567",
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "nationality": "CAN",
        "date_of_birth": "950523",
        "sex": "M",
        "expiry_date": "320523",
        "passport_no": "AB1234567",
        "date_of_issue": "220523",
        "place_of_birth": "TORONTO",
    }
    return json.dumps(sample, indent=2)


def _document_defaults(doc_kind: str) -> str:
    """Return default JSON for a selected document type."""
    if doc_kind == "Passport":
        return _default_passport_fields()
    return _default_pr_fields()


def _pr_sample_choices() -> list[str]:
    """Return saved PR sample names."""
    return list(_BUILTIN_PR_SAMPLES.keys()) + _pr_store.list_names()


def _refresh_pr_samples():
    """Refresh PR sample dropdown choices."""
    names = _pr_sample_choices()
    value = names[0] if names else None
    return gr.update(choices=names, value=value)


def _load_pr_sample(sample_name: str):
    """Load a saved PR sample into the editor."""
    if not sample_name:
        return _default_pr_fields(), "Select a saved PR sample first."
    if sample_name in _BUILTIN_PR_SAMPLES:
        return (
            json.dumps(_BUILTIN_PR_SAMPLES[sample_name], indent=2),
            f"Loaded built-in PR template '{sample_name}'.",
        )
    fields = _pr_store.load(sample_name)
    if not fields:
        return _default_pr_fields(), f"No saved PR sample named '{sample_name}'."
    return json.dumps(fields, indent=2), f"Loaded PR sample '{sample_name}'."


def _save_pr_sample(sample_name: str, fields_json: str):
    """Save the current PR fields as a reusable sample."""
    if not sample_name or not sample_name.strip():
        return _refresh_pr_samples(), "Enter a sample name first."
    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as exc:
        return _refresh_pr_samples(), f"Invalid JSON: {exc}"

    _pr_store.save(sample_name.strip(), fields)
    updated = _refresh_pr_samples()
    return updated, f"Saved PR sample '{sample_name.strip()}'."


def _document_provider_status() -> str:
    """Return a non-sensitive summary of local provider configuration."""
    return provider_status_markdown()


def _to_pil_image(image_value):
    """Convert Gradio image data to PIL if present."""
    if image_value is None:
        return None
    if isinstance(image_value, Image.Image):
        return image_value
    return Image.fromarray(image_value)


def _load_font_safe(size: int, bold: bool = False):
    """Load a local font with robust fallbacks."""
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "cour.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for item in candidates:
        try:
            return ImageFont.truetype(item, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _format_pr_date(value: str) -> str:
    """Convert YYMMDD-style values to PR display style, best effort."""
    raw = (value or "").strip().replace("-", "")
    if len(raw) == 6 and raw.isdigit():
        yy = raw[0:2]
        mm = int(raw[2:4])
        dd = raw[4:6]
        months = {
            1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
            7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
        }
        mon = months.get(mm, "JAN")
        return f"{dd} {mon} / {mon} {yy}"
    return value


def _render_pr_on_uploaded_template(fields: dict[str, str], photo: Image.Image, template_bg: Image.Image):
    """Render PR content on top of a user-uploaded front template image."""
    bg = template_bg.convert("RGB")

    # Auto-crop dark tabletop/background so coordinates map to the card itself.
    gray = bg.convert("L")
    bbox = gray.point(lambda p: 255 if p > 22 else 0).getbbox()
    if bbox:
        bg = bg.crop(bbox)

    card = bg.resize((1011, 637), Image.LANCZOS)
    draw = ImageDraw.Draw(card)

    # Clear variable zones to avoid stacking text/photo over already-filled sample cards.
    draw.rectangle([(48, 88), (440, 600)], fill=(242, 242, 242))      # photo area
    draw.rectangle([(485, 108), (958, 545)], fill=(242, 242, 242))     # text area

    # Subtle noise blending to avoid harsh rectangular patches.
    for y in range(90, 600, 6):
        draw.line([(48, y), (958, y)], fill=(236, 236, 236), width=1)

    # Photo zone aligned to sample front layout.
    pw, ph = 380, 500
    px, py = 58, 95
    photo_rgb = photo.convert("RGB")
    ratio_src = photo_rgb.width / max(1, photo_rgb.height)
    ratio_dst = pw / ph
    if ratio_src > ratio_dst:
        new_w = int(photo_rgb.height * ratio_dst)
        left = (photo_rgb.width - new_w) // 2
        photo_rgb = photo_rgb.crop((left, 0, left + new_w, photo_rgb.height))
    else:
        new_h = int(photo_rgb.width / ratio_dst)
        top = (photo_rgb.height - new_h) // 2
        photo_rgb = photo_rgb.crop((0, top, photo_rgb.width, top + new_h))
    photo_rgb = photo_rgb.resize((pw, ph), Image.LANCZOS)
    card.paste(photo_rgb, (px, py))

    title_font = _load_font_safe(28, bold=True)
    value_font = _load_font_safe(50, bold=True)
    normal_font = _load_font_safe(24, bold=True)

    surname = (fields.get("surname") or "").upper()
    given = (fields.get("given_names") or "").upper()
    doc_no = (fields.get("pr_number") or fields.get("document_number") or "").upper()
    sex = (fields.get("sex") or "").upper()
    nationality = (fields.get("nationality") or "CAN").upper()
    dob = _format_pr_date(fields.get("date_of_birth", ""))
    expiry = _format_pr_date(fields.get("expiry_date", ""))

    # Field positions tuned against provided sample fronts.
    draw.text((500, 118), surname, font=title_font, fill="#111111")
    draw.text((500, 164), given, font=title_font, fill="#222222")
    draw.text((500, 232), doc_no, font=value_font, fill="#111111")
    draw.text((500, 315), sex[:1], font=normal_font, fill="#111111")
    draw.text((585, 315), nationality[:3], font=normal_font, fill="#111111")
    draw.text((500, 415), dob, font=normal_font, fill="#111111")
    draw.text((500, 485), expiry, font=normal_font, fill="#111111")

    return card


def _generate_document_preview(doc_kind: str, fields_json: str, photo_image, template_bg_image):
    """Generate a template-driven PR card or passport preview."""
    if not fields_json or not fields_json.strip():
        return None, "Enter field JSON first.", ""

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}", ""

    photo = _to_pil_image(photo_image)
    if photo is None:
        return None, "Upload a portrait image first.", ""

    custom_bg = _to_pil_image(template_bg_image)

    from canada_id.templates.generator import generate_passport, generate_pr_card

    if doc_kind == "Passport":
        generated = generate_passport(fields, photo=photo)
        image_out = generated.image
        stem = "passport"
    else:
        if custom_bg is not None:
            image_out = _render_pr_on_uploaded_template(fields, photo, custom_bg)
            generated = None
        else:
            generated = generate_pr_card(fields, photo=photo)
            image_out = generated.image
        stem = "pr_card"

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    image_out.save(output_path)

    lines = [
        f"Generated {doc_kind} at {image_out.width}x{image_out.height}px.",
        f"Saved to {output_path}",
    ]
    if generated and generated.mrz_string:
        lines.append("")
        lines.append("MRZ:")
        lines.append(generated.mrz_string)
    if generated and generated.warnings:
        lines.append("")
        lines.extend(f"Warning: {item}" for item in generated.warnings)
    if custom_bg is not None and doc_kind != "Passport":
        lines.append("")
        lines.append("Used uploaded PR template background for real-time front rendering.")

    return image_out, "\n".join(lines), str(output_path)


def _clamp_enhance(value: float) -> float:
    """Clamp enhancement values to a safe range."""
    return max(0.5, min(2.0, value))


def _apply_edit_plan(image: Image.Image, plan: EditPlan) -> Image.Image:
    """Apply an enhancement plan using PIL."""
    output = image.convert("RGB")
    output = ImageEnhance.Brightness(output).enhance(_clamp_enhance(plan.brightness))
    output = ImageEnhance.Contrast(output).enhance(_clamp_enhance(plan.contrast))
    output = ImageEnhance.Color(output).enhance(_clamp_enhance(plan.color))
    output = ImageEnhance.Sharpness(output).enhance(_clamp_enhance(plan.sharpness))
    return output


def _local_plan_from_prompt(prompt: str) -> EditPlan:
    """Build a deterministic local enhancement plan from keywords."""
    text = (prompt or "").lower()
    brightness = 1.0
    contrast = 1.0
    color = 1.0
    sharpness = 1.0

    if "bright" in text or "light" in text:
        brightness += 0.15
    if "dark" in text:
        brightness -= 0.15
    if "contrast" in text or "crisp" in text:
        contrast += 0.2
    if "soft" in text:
        sharpness -= 0.15
    if "sharp" in text or "clear" in text:
        sharpness += 0.2
    if "vivid" in text or "saturat" in text or "color" in text:
        color += 0.2
    if "muted" in text or "desatur" in text:
        color -= 0.2

    return EditPlan(
        brightness=_clamp_enhance(brightness),
        contrast=_clamp_enhance(contrast),
        color=_clamp_enhance(color),
        sharpness=_clamp_enhance(sharpness),
    )


def _plan_from_openrouter(prompt: str, model: str) -> tuple[EditPlan | None, str]:
    """Request enhancement parameters from OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None, "OPENROUTER_API_KEY missing; used local enhancement plan."

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an image-retouch planner. Return only JSON with keys "
                    "brightness, contrast, color, sharpness as numbers in range 0.5..2.0."
                ),
            },
            {
                "role": "user",
                "content": f"Edit request: {prompt}",
            },
        ],
        "temperature": 0.2,
    }

    req = request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return (
            EditPlan(
                brightness=_clamp_enhance(float(parsed.get("brightness", 1.0))),
                contrast=_clamp_enhance(float(parsed.get("contrast", 1.0))),
                color=_clamp_enhance(float(parsed.get("color", 1.0))),
                sharpness=_clamp_enhance(float(parsed.get("sharpness", 1.0))),
            ),
            f"Used OpenRouter model {model}.",
        )
    except (error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return None, "OpenRouter plan unavailable; used local enhancement plan."


def _enhance_document_image(
    image_value,
    edit_prompt: str,
    provider: str,
    model: str,
):
    """Enhance generated image with provider-assisted or local plan."""
    image = _to_pil_image(image_value)
    if image is None:
        return None, "Generate or upload an image first.", ""

    message = "Used local enhancement plan."
    plan = None
    if provider == "OpenRouter":
        plan, message = _plan_from_openrouter(edit_prompt, model)

    if plan is None:
        plan = _local_plan_from_prompt(edit_prompt)

    enhanced = _apply_edit_plan(image, plan)
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    enhanced.save(output_path)

    plan_text = (
        f"Plan => brightness={plan.brightness:.2f}, contrast={plan.contrast:.2f}, "
        f"color={plan.color:.2f}, sharpness={plan.sharpness:.2f}"
    )
    return enhanced, f"{message}\n{plan_text}\nSaved to {output_path}", str(output_path)


def create_app() -> gr.Blocks:
    """Create the Gradio application."""
    choices = _province_choices()

    with gr.Blocks(title="moviepropIDgen") as app:
        gr.Markdown("# moviepropIDgen")
        gr.Markdown(
            "Encode and decode AAMVA-standard PDF417 barcodes"
            " for all Canadian provinces and territories."
            " **All operations are saved automatically.**"
        )

        with gr.Tab("Decode"):
            gr.Markdown("Upload an image containing a PDF417 barcode.")
            with gr.Row():
                decode_input = gr.Image(label="Barcode Image")
                with gr.Column():
                    decode_fields = gr.Textbox(
                        label="Parsed Fields", lines=15,
                    )
                    decode_raw = gr.Textbox(
                        label="Raw AAMVA String", lines=5,
                    )
                    decode_province = gr.Textbox(
                        label="Detected Province", lines=1,
                    )
            decode_btn = gr.Button("Decode", variant="primary")
            decode_btn.click(
                _decode_image,
                inputs=[decode_input],
                outputs=[decode_fields, decode_raw, decode_province],
            )

        with gr.Tab("Encode"):
            gr.Markdown(
                "Generate a PDF417 barcode from AAMVA field data."
                " **Province is validated against your data** —"
                " mismatches are blocked."
            )
            with gr.Row():
                with gr.Column():
                    encode_province = gr.Dropdown(
                        choices=choices,
                        label="Province/Territory",
                    )
                    encode_fields = gr.Textbox(
                        label="Fields (JSON)",
                        lines=15,
                        value=_sample_fields(),
                    )
                    with gr.Row():
                        encode_btn = gr.Button(
                            "Generate Barcode", variant="primary",
                        )
                        validate_btn = gr.Button("Validate")
                        autodetect_btn = gr.Button(
                            "Auto-Detect Province",
                        )
                with gr.Column():
                    encode_output = gr.Image(label="Generated Barcode")
                    encode_aamva = gr.Textbox(
                        label="AAMVA String", lines=5,
                    )
                    encode_status = gr.Textbox(
                        label="Status", lines=2,
                    )
                    validate_output = gr.Textbox(
                        label="Validation Result", lines=5,
                    )
            encode_btn.click(
                _encode_barcode,
                inputs=[encode_province, encode_fields],
                outputs=[encode_output, encode_aamva, encode_status],
            )
            validate_btn.click(
                _validate_fields,
                inputs=[encode_province, encode_fields],
                outputs=[validate_output],
            )
            autodetect_btn.click(
                _auto_detect_province,
                inputs=[encode_fields],
                outputs=[encode_province, encode_status],
            )

        with gr.Tab("MRZ"):
            gr.Markdown("## Canadian MRZ - Passport & PR Card")
            gr.Markdown(
                "**Passport** = TD3 (2x44) |"
                " **PR Card** = TD1 (3x30) |"
                " Issuing country is always CAN."
            )

            # ── Section 1: Generate ──
            gr.Markdown("### 1. Generate MRZ")
            with gr.Row():
                mrz_doc_selector = gr.Dropdown(
                    choices=_doc_type_choices(),
                    label="Load Template",
                    info="Select a Canadian document type"
                    " to fill sample data",
                )
                load_template_btn = gr.Button(
                    "Load Template",
                    variant="secondary",
                )
                fill_btn = gr.Button(
                    "Fill from Scan/Parse",
                    variant="secondary",
                )

            # Educational info: card era / chip type / doc# format
            mrz_doc_info = gr.Markdown(
                "Select a template to see card era, chip type, and"
                " document number format details."
            )
            mrz_doc_selector.change(
                _show_doc_info,
                inputs=[mrz_doc_selector],
                outputs=[mrz_doc_info],
            )

            # ── Era toggle: passport (legacy/current) + PR (3 eras) ──
            with gr.Row():
                mrz_passport_era = gr.Radio(
                    choices=[
                        "Pre-May 2023 (legacy: AB123456)",
                        "Post-May 2023 (current: A123456BC)",
                    ],
                    value="Post-May 2023 (current: A123456BC)",
                    label="Passport Era (TD3 only)",
                    info="Affects expected document number format",
                )
                mrz_pr_era = gr.Radio(
                    choices=[
                        "2002-2009 (PDF417 + magstripe)",
                        "2009-2014 (PDF417 + optical stripe)",
                        "2015-present (RFID, no PDF417)",
                    ],
                    value="2015-present (RFID, no PDF417)",
                    label="PR Card Era (TD1 only)",
                    info="Affects security features (informational)",
                )

            # ── JSON paste — same UX as Encode tab ──
            gr.Markdown("**Paste JSON to auto-fill fields:**")
            with gr.Row():
                mrz_json_input = gr.Textbox(
                    label="JSON payload",
                    lines=10,
                    placeholder=(
                        "{\n"
                        '  "Document Type": "P",\n'
                        '  "MRZ Format": "TD3",\n'
                        '  "Issuing Country": "CAN",\n'
                        '  "Document Number": "AB123456",\n'
                        '  "Surname": "RAHMAN",\n'
                        '  "Given Names": "BADR",\n'
                        '  "Nationality": "CAN",\n'
                        '  "Sex": "M",\n'
                        '  "Date of Birth": "970614",\n'
                        '  "Expiry Date": "280701",\n'
                        '  "Optional Data 1": "",\n'
                        '  "Issuing Authority": "GATINEAU"\n'
                        "}"
                    ),
                )
                mrz_json_load_btn = gr.Button(
                    "Load from JSON",
                    variant="secondary",
                )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Document Info**")
                    mrz_doc_type = gr.Dropdown(
                        choices=["P", "CA", "I", "AC", "C"],
                        value="CA",
                        label="Document Type",
                        info=(
                            "P=Passport (TD3) | CA=Canadian PR Card"
                            " (TD1) | I=Generic ID | AC=Crew member"
                        ),
                        allow_custom_value=True,
                    )
                    mrz_format = gr.Dropdown(
                        choices=["TD1", "TD2", "TD3"],
                        value="TD1",
                        label="MRZ Format"
                        " (TD3=Passport, TD1=PR Card)",
                    )
                    mrz_country = gr.Textbox(
                        label="Issuing Country (3-letter)",
                        value="CAN",
                    )
                    mrz_doc_num = gr.Textbox(
                        label="Document Number"
                        " (max 9 chars)",
                        value="PD0183017",
                    )

                with gr.Column():
                    gr.Markdown("**Personal Info**")
                    mrz_surname = gr.Textbox(
                        label="Surname (family name)",
                        value="MAGHA MOFFO",
                    )
                    mrz_given = gr.Textbox(
                        label="Given Names"
                        " (space-separated)",
                        value="MATHILDE",
                    )
                    mrz_nationality = gr.Textbox(
                        label="Nationality (3-letter)"
                        " - can differ from issuing country",
                        value="CMR",
                    )
                    mrz_sex = gr.Dropdown(
                        choices=["M", "F", "X"], value="F",
                        label="Sex",
                    )

                with gr.Column():
                    gr.Markdown("**Dates & Optional**")
                    mrz_dob = gr.Textbox(
                        label="Date of Birth (YYMMDD)",
                        value="841127",
                    )
                    mrz_expiry = gr.Textbox(
                        label="Expiry Date (YYMMDD)",
                        value="260430",
                    )
                    mrz_opt1 = gr.Textbox(
                        label="Optional Data 1"
                        " (TD1: province | TD3: personal number)",
                        value="ON",
                    )
                    mrz_opt2 = gr.Textbox(
                        label="Optional Data 2"
                        " (TD1 only)",
                        value="",
                    )

            mrz_gen_btn = gr.Button(
                "Generate MRZ", variant="primary",
            )
            with gr.Row():
                mrz_gen_output = gr.Textbox(
                    label="Generated MRZ", lines=4,
                )
                mrz_gen_image = gr.Image(
                    label="MRZ Image",
                )
            mrz_gen_status = gr.Textbox(
                label="Status", lines=1,
            )

            # ── All generate fields list ──
            _gen_fields = [
                mrz_doc_type, mrz_format, mrz_country,
                mrz_surname, mrz_given, mrz_doc_num,
                mrz_nationality, mrz_dob, mrz_sex,
                mrz_expiry, mrz_opt1, mrz_opt2,
            ]

            load_template_btn.click(
                _load_doc_template,
                inputs=[mrz_doc_selector],
                outputs=_gen_fields,
            )
            mrz_json_load_btn.click(
                _mrz_load_from_json,
                inputs=[mrz_json_input],
                outputs=_gen_fields + [mrz_gen_status],
            )
            mrz_gen_btn.click(
                _mrz_generate,
                inputs=_gen_fields,
                outputs=[
                    mrz_gen_output, mrz_gen_image,
                    mrz_gen_status,
                ],
            )

            # ── Section 2: Scan from Image ──
            gr.Markdown("---")
            gr.Markdown("### 2. Scan Document")
            gr.Markdown(
                "Upload a passport or PR card photo."
                " MRZ is extracted automatically."
                " If OCR fails, paste the MRZ text"
                " manually below."
            )
            with gr.Row():
                with gr.Column():
                    mrz_scan_img = gr.Image(
                        label="Upload Document Image",
                    )
                    mrz_scan_btn = gr.Button(
                        "Extract MRZ from Image",
                        variant="primary",
                    )
                with gr.Column():
                    mrz_scan_text = gr.Textbox(
                        label="Extracted MRZ", lines=4,
                    )
                    mrz_scan_parsed = gr.Textbox(
                        label="Parsed Fields", lines=12,
                    )
                    mrz_scan_status = gr.Textbox(
                        label="Scan Status", lines=1,
                    )
            mrz_scan_btn.click(
                _mrz_scan_image,
                inputs=[mrz_scan_img],
                outputs=[
                    mrz_scan_text, mrz_scan_parsed,
                    mrz_scan_status,
                ],
            )

            # Fill from scan wiring — uses whichever
            # parsed result has data (scan or paste)
            fill_btn.click(
                _mrz_fill_from_scan,
                inputs=[mrz_scan_parsed],
                outputs=_gen_fields + [mrz_gen_status],
            )

            # ── Section 2b: Manual paste ──
            gr.Markdown("---")
            gr.Markdown(
                "### Or paste MRZ text manually"
            )
            gr.Markdown(
                "If OCR fails, type/paste the MRZ"
                " lines here. Then click **Parse**"
                " and **Fill from Paste** to load"
                " into the generator."
            )
            with gr.Row():
                mrz_paste_input = gr.Textbox(
                    label="Paste MRZ text here",
                    lines=4,
                    placeholder=(
                        "CACANPD01830178<1110153398"
                        "<<<5\n8411279F2604309CMR<"
                        "210430<01<4\nMAGHA<MOFFO<<"
                        "MATHILDE<<<<<<<<<"
                    ),
                )
                mrz_paste_ocr = gr.Checkbox(
                    label="Apply OCR correction",
                    value=True,
                )
            with gr.Row():
                mrz_paste_btn = gr.Button(
                    "Parse & Validate",
                    variant="primary",
                )
                mrz_paste_fill_btn = gr.Button(
                    "Fill from Paste",
                )
            mrz_paste_result = gr.Textbox(
                label="Parsed Fields", lines=12,
            )
            mrz_paste_status = gr.Textbox(
                label="Status", lines=1,
            )
            mrz_paste_btn.click(
                _mrz_parse_text,
                inputs=[mrz_paste_input, mrz_paste_ocr],
                outputs=[
                    mrz_paste_result, mrz_paste_status,
                ],
            )
            mrz_paste_fill_btn.click(
                _mrz_fill_from_scan,
                inputs=[mrz_paste_result],
                outputs=_gen_fields + [mrz_gen_status],
            )

            # ── Section 3: Compare ──
            gr.Markdown("---")
            gr.Markdown("### 3. Compare Generated vs Scanned")
            gr.Markdown(
                "After generating and scanning, click"
                " Compare to verify they match."
            )
            mrz_compare_btn = gr.Button(
                "Compare", variant="primary",
            )
            mrz_compare_result = gr.Textbox(
                label="Comparison Result", lines=5,
            )
            mrz_compare_btn.click(
                _mrz_compare,
                inputs=[mrz_gen_output, mrz_scan_text],
                outputs=[mrz_compare_result],
            )

            # ── Section 4: Export ──
            gr.Markdown("---")
            gr.Markdown("### 4. Export Results")
            with gr.Row():
                mrz_export_txt_btn = gr.Button("Export TXT")
                mrz_export_json_btn = gr.Button("Export JSON")
            mrz_export_output = gr.Textbox(
                label="Export Output (copy or save)", lines=10,
            )
            mrz_export_txt_btn.click(
                _mrz_export_txt,
                inputs=[
                    mrz_gen_output, mrz_scan_parsed,
                    mrz_gen_status,
                ],
                outputs=[mrz_export_output],
            )
            mrz_export_json_btn.click(
                _mrz_export_json,
                inputs=[
                    mrz_gen_output, mrz_scan_parsed,
                    mrz_gen_status,
                ],
                outputs=[mrz_export_output],
            )


        with gr.Tab("More Tools"):
            gr.Markdown(
                "Additional tools (under active development). "
                "Click any tab below to expand."
            )
            with gr.Tabs():
                with gr.Tab("Documents"):
                    gr.Markdown("## Local Document Studio")
                    gr.Markdown(
                        "Generate template-driven Canadian documents locally. "
                        "PR card presets can be saved and reused with new photos or updated info."
                    )
                    with gr.Row():
                        with gr.Column(scale=1):
                            doc_kind = gr.Dropdown(
                                choices=["Permanent Resident Card", "Passport"],
                                value="Permanent Resident Card",
                                label="Document Type",
                            )
                            pr_sample_name = gr.Textbox(
                                label="PR Sample Name",
                                placeholder="e.g. default_pr_layout",
                            )
                            pr_sample_list = gr.Dropdown(
                                choices=_pr_sample_choices(),
                                label="Saved PR Samples",
                            )
                            with gr.Row():
                                doc_load_defaults = gr.Button("Load Default Fields")
                                pr_load_btn = gr.Button("Load PR Sample")
                                pr_save_btn = gr.Button("Save PR Sample")
                            doc_photo = gr.Image(label="Portrait Photo")
                            doc_template_bg = gr.Image(
                                label="Optional PR Front Template Background",
                            )
                            doc_fields = gr.Textbox(
                                label="Document Fields (JSON)",
                                lines=18,
                                value=_default_pr_fields(),
                            )
                            doc_generate_btn = gr.Button(
                                "Generate Document",
                                variant="primary",
                            )
                            doc_edit_prompt = gr.Textbox(
                                label="Edit Prompt",
                                lines=2,
                                placeholder="e.g. make it sharper, slightly brighter, and improve contrast",
                            )
                            with gr.Row():
                                doc_edit_provider = gr.Dropdown(
                                    choices=["Local", "OpenRouter"],
                                    value="Local",
                                    label="Edit Provider",
                                )
                                doc_edit_model = gr.Textbox(
                                    label="Provider Model",
                                    value="openai/gpt-4o-mini",
                                )
                            doc_enhance_btn = gr.Button("Enhance Image")
                        with gr.Column(scale=1):
                            doc_output = gr.Image(label="Generated Document")
                            doc_status = gr.Textbox(label="Status", lines=12)
                            doc_saved_path = gr.Textbox(label="Saved File", lines=1)
                    doc_load_defaults.click(
                        _document_defaults,
                        inputs=[doc_kind],
                        outputs=[doc_fields],
                    )
                    doc_kind.change(
                        _document_defaults,
                        inputs=[doc_kind],
                        outputs=[doc_fields],
                    )
                    pr_load_btn.click(
                        _load_pr_sample,
                        inputs=[pr_sample_list],
                        outputs=[doc_fields, doc_status],
                    )
                    pr_save_btn.click(
                        _save_pr_sample,
                        inputs=[pr_sample_name, doc_fields],
                        outputs=[pr_sample_list, doc_status],
                    )
                    doc_generate_btn.click(
                        _generate_document_preview,
                        inputs=[doc_kind, doc_fields, doc_photo, doc_template_bg],
                        outputs=[doc_output, doc_status, doc_saved_path],
                    )
                    doc_enhance_btn.click(
                        _enhance_document_image,
                        inputs=[doc_output, doc_edit_prompt, doc_edit_provider, doc_edit_model],
                        outputs=[doc_output, doc_status, doc_saved_path],
                    )

                with gr.Tab("AI Generator"):
                    gr.Markdown("## Synthetic Identity Engine")
                    gr.Markdown(
                        "Generate highly realistic, mathematically valid synthetic Canadian identities using AI. "
                        "Output matches the exact AAMVA or MRZ JSON formats required for generation."
                    )
                    with gr.Row():
                        with gr.Column():
                            ai_gen_type = gr.Dropdown(
                                choices=["ON - Ontario", "QC - Quebec", "PR Card", "Passport"],
                                value="ON - Ontario",
                                label="Identity Type",
                            )
                            ai_gen_age = gr.Textbox(
                                label="Age Range",
                                value="25-35",
                                placeholder="e.g. 25-35, 40-50, exactly 21",
                            )
                            ai_gen_sex = gr.Dropdown(
                                choices=["Random", "M", "F", "X"],
                                value="Random",
                                label="Sex",
                            )
                            ai_gen_btn = gr.Button("Generate Synthetic Identity", variant="primary")
                        with gr.Column():
                            ai_gen_output = gr.Textbox(
                                label="Generated Identity (JSON)",
                                lines=15,
                            )
            
                    def _generate_synthetic_identity_ui(doc_type: str, age: str, sex: str) -> str:
                        from canada_id.ai_agents.synthetic_data import generate_synthetic_identity
                        result = generate_synthetic_identity(doc_type, age, sex)
                        return json.dumps(result, indent=2)
            
                    ai_gen_btn.click(
                        _generate_synthetic_identity_ui,
                        inputs=[ai_gen_type, ai_gen_age, ai_gen_sex],
                        outputs=[ai_gen_output],
                    )

                with gr.Tab("AI Config"):
                    gr.Markdown("## Local Provider Configuration")
                    gr.Markdown(
                        "Provider keys are read from environment variables or a local .env file. "
                        "This app does not store or display full secrets."
                    )
                    provider_status = gr.Markdown(value=_document_provider_status())
                    provider_refresh = gr.Button("Refresh Provider Status", variant="primary")
                    provider_refresh.click(
                        _document_provider_status,
                        outputs=[provider_status],
                    )

                with gr.Tab("History"):
                    gr.Markdown("## Operation History")
                    gr.Markdown("All encodes, decodes, and validations are saved.")
                    with gr.Row():
                        history_op = gr.Dropdown(
                            choices=["all", "encode", "decode", "validate"],
                            value="all",
                            label="Filter by type",
                        )
                        history_province = gr.Textbox(
                            label="Filter by province (e.g. ON, QC)",
                            placeholder="Leave blank for all",
                        )
                        history_btn = gr.Button("Refresh", variant="primary")
                    history_table = gr.Dataframe(
                        headers=[
                            "ID", "Timestamp", "Type",
                            "Province", "Summary", "Errors?",
                        ],
                        label="Recent Operations",
                    )
                    history_btn.click(
                        _get_history_table,
                        inputs=[history_op, history_province],
                        outputs=[history_table],
                    )

                with gr.Tab("Code 39"):
                    gr.Markdown(
                        "## Code 39 Barcode Generator"
                    )
                    gr.Markdown(
                        "Encode text as a Code 39 (1D) barcode."
                        " Supports A-Z, 0-9, and -.$/+% characters."
                    )
                    with gr.Row():
                        with gr.Column():
                            c39_text = gr.Textbox(
                                label="Text to encode",
                                placeholder="e.g. HELLO123",
                                value="HELLO123",
                            )
                            c39_btn = gr.Button(
                                "Generate Code 39", variant="primary",
                            )
                        with gr.Column():
                            c39_output = gr.Image(label="Code 39 Barcode")
                            c39_status = gr.Textbox(
                                label="Status", lines=1,
                            )
                    c39_btn.click(
                        _generate_code39,
                        inputs=[c39_text],
                        outputs=[c39_output, c39_status],
                    )

                with gr.Tab("Compositor"):
                    gr.Markdown(
                        "## Card Compositor"
                    )
                    gr.Markdown(
                        "Overlay a barcode onto a card template."
                        " Position and size are set as fractions"
                        " of the card dimensions (0.0 to 1.0)."
                    )
                    with gr.Row():
                        with gr.Column():
                            comp_card = gr.Image(
                                label="Card Template (upload image)",
                            )
                            comp_barcode = gr.Image(
                                label="Barcode Image (upload image)",
                            )
                        with gr.Column():
                            with gr.Row():
                                comp_x = gr.Number(
                                    label="X position", value=0.02,
                                    minimum=0.0, maximum=1.0,
                                )
                                comp_y = gr.Number(
                                    label="Y position", value=0.05,
                                    minimum=0.0, maximum=1.0,
                                )
                            with gr.Row():
                                comp_w = gr.Number(
                                    label="Width", value=0.37,
                                    minimum=0.01, maximum=1.0,
                                )
                                comp_h = gr.Number(
                                    label="Height", value=0.90,
                                    minimum=0.01, maximum=1.0,
                                )
                            comp_rot = gr.Number(
                                label="Rotation (degrees)", value=-90.0,
                            )
                            comp_btn = gr.Button(
                                "Composite", variant="primary",
                            )
                    comp_result = gr.Image(label="Result")
                    comp_status = gr.Textbox(label="Status", lines=1)
                    comp_btn.click(
                        _composite_card,
                        inputs=[
                            comp_card, comp_barcode,
                            comp_x, comp_y, comp_w, comp_h, comp_rot,
                        ],
                        outputs=[comp_result, comp_status],
                    )

                with gr.Tab("MRZ Guide"):
                    gr.HTML(get_mrz_guide_html())

                with gr.Tab("Provinces"):
                    gr.Markdown("## Canadian Province & Territory Profiles")
                    rows = []
                    for p in all_profiles():
                        classes = ", ".join(p.vehicle_classes.keys())
                        rows.append([
                            p.code, p.name, p.iin,
                            f"v{p.aamva_version}", classes,
                        ])
                    gr.Dataframe(
                        value=rows,
                        headers=[
                            "Code", "Name", "IIN",
                            "AAMVA Version", "Vehicle Classes",
                        ],
                    )

        # Stats footer
        stats = _db.get_stats()
        total = sum(stats.values())
        if total > 0:
            gr.Markdown(
                f"*Lifetime stats: {stats.get('encode', 0)} encodes,"
                f" {stats.get('decode', 0)} decodes,"
                f" {stats.get('validate', 0)} validations*"
            )

    return app


def launch():
    """Launch the Gradio web UI."""
    app = create_app()
    app.launch(share=False)


if __name__ == "__main__":
    launch()
