"""Gradio web UI for canada-id barcode encoding and decoding."""
import json

import gradio as gr
from PIL import Image

from canada_id.guards import auto_fix_province, check_province_match
from canada_id.provinces.registry import all_profiles, get_profile
from canada_id.storage import HistoryDB

_db = HistoryDB()


def _province_choices() -> list[str]:
    """Build province dropdown choices."""
    return [f"{p.code} - {p.name}" for p in all_profiles()]


def _extract_code(choice: str) -> str:
    """Extract province code from dropdown choice string."""
    return choice.split(" - ")[0].strip().upper() if choice else ""


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
    """Format an MrzResult into readable text."""
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
    if result.optional_data_1:
        lines.append(f"Optional 1: {result.optional_data_1}")
    if result.optional_data_2:
        lines.append(f"Optional 2: {result.optional_data_2}")
    if result.personal_number:
        lines.append(f"Personal Number: {result.personal_number}")
    if result.birth_date:
        lines.append(f"Birth Date: {result.birth_date.isoformat()}")
    if result.expiry_date_parsed:
        lines.append(
            f"Expiry Date: {result.expiry_date_parsed.isoformat()}"
        )
    return "\n".join(lines)


def _load_passport_template():
    """Load sample Canadian Passport (TD3) fields."""
    return (
        "P", "TD3", "CAN",
        "SMITH", "JOHN MICHAEL",
        "AB1234567", "CAN",
        "900115", "M", "280115",
        "",        # optional_data_1 (personal number for TD3)
        "",        # optional_data_2 (TD1 only)
    )


def _load_pr_template():
    """Load sample Canadian PR Card (TD1) fields."""
    return (
        "I", "TD1", "CAN",
        "MAGHA MOFFO", "MATHILDE",
        "PD0183017", "CMR",
        "841127", "F", "260430",
        "ON",      # optional_data_1
        "",        # optional_data_2
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


def _mrz_generate(
    doc_type, mrz_format, country, surname, given_names,
    doc_num, nationality, dob, sex, expiry, opt1, opt2,
):
    """Generate MRZ from form fields with input validation."""
    from canada_id.mrz.generator import MRZData, generate_mrz
    from canada_id.mrz.renderer import render_mrz_image
    from canada_id.mrz.utils import lines_from_mrz

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

    # Validate with clear field-level errors
    errors = []
    if not surname_clean:
        errors.append("Surname is required")
    if not doc_num:
        errors.append("Document Number is required")
    if len(doc_num) > 9:
        errors.append(
            f"Document Number too long: '{doc_num}'"
            f" ({len(doc_num)} chars, max 9)"
        )
    if not country or len(country) != 3:
        errors.append(
            f"Issuing Country must be 3 letters,"
            f" got '{country}'"
        )
    if not nationality or len(nationality) != 3:
        errors.append(
            f"Nationality must be 3 letters,"
            f" got '{nationality}'"
        )
    if dob and len(dob) != 6:
        errors.append(
            f"Date of Birth must be YYMMDD (6 digits),"
            f" got '{dob}' ({len(dob)} chars)"
        )
    if expiry and len(expiry) != 6:
        errors.append(
            f"Expiry Date must be YYMMDD (6 digits),"
            f" got '{expiry}' ({len(expiry)} chars)"
        )
    if errors:
        return "", None, "FIELD ERRORS:\n" + "\n".join(errors)

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
        return display, img, f"OK - {mrz_format} generated"
    except (ValueError, Exception) as e:
        return "", None, f"Error: {e}"


def _mrz_scan_image(image, crop_top, crop_bottom):
    """Extract MRZ from uploaded document image via OCR."""
    if image is None:
        return None, "", "", (
            "Upload a passport or PR card image."
        )

    from canada_id.mrz.ocr_reader import extract_mrz_from_image
    from canada_id.mrz.parsers import MrzParseError, parse_mrz
    from canada_id.mrz.utils import lines_from_mrz

    pil_image = Image.fromarray(image)

    # Apply crop if user adjusted sliders
    top_pct = float(crop_top or 0) / 100.0
    bot_pct = float(crop_bottom or 100) / 100.0
    if top_pct > 0 or bot_pct < 1.0:
        w, h = pil_image.size
        y1 = int(h * top_pct)
        y2 = int(h * bot_pct)
        if y2 > y1 + 10:
            pil_image = pil_image.crop((0, y1, w, y2))

    # Show the cropped preview
    import numpy as np
    crop_preview = np.array(pil_image)

    mrz_text = extract_mrz_from_image(pil_image)

    if not mrz_text:
        return crop_preview, "", "", (
            "Could not extract MRZ. Try adjusting"
            " the crop sliders to isolate the MRZ zone"
            " (the 2-3 lines of <<< text at the bottom)."
        )

    lines = lines_from_mrz(mrz_text)
    display = "\n".join(lines)

    try:
        result = parse_mrz(
            mrz_text, ocr_correct=True, canada_only=False,
        )
        parsed = _mrz_result_text(result)
        valid = "VALID" if result.check_digits_valid else "INVALID"
        status = f"Extracted and parsed. Check digits: {valid}"
        return crop_preview, display, parsed, status
    except MrzParseError as e:
        return crop_preview, display, "", (
            f"Extracted MRZ but parse failed: {e}"
            f" - Try adjusting crop sliders."
        )
    except ValueError as e:
        return crop_preview, display, "", (
            f"Extracted but validation failed: {e}"
        )


def _mrz_fill_from_scan(scan_parsed):
    """Fill generate form from scanned/parsed MRZ fields."""
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
        )
        parsed = _mrz_result_text(result)
        valid = "VALID" if result.check_digits_valid else "INVALID"
        return parsed, f"Check digits: {valid}"
    except MrzParseError as e:
        return "", f"Parse error: {e}"
    except ValueError as e:
        return "", f"Validation error: {e}"


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


def create_app() -> gr.Blocks:
    """Create the Gradio application."""
    choices = _province_choices()

    with gr.Blocks(title="Canada ID - AAMVA Barcode Tool") as app:
        gr.Markdown("# Canada ID - AAMVA PDF417 Barcode Tool")
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
                passport_btn = gr.Button(
                    "Passport Template (TD3)",
                )
                pr_btn = gr.Button(
                    "PR Card Template (TD1)",
                )
                fill_btn = gr.Button(
                    "Fill from Scan/Parse",
                    variant="secondary",
                )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Document Info**")
                    mrz_doc_type = gr.Dropdown(
                        choices=["I", "P"], value="I",
                        label="Document Type"
                        " (P=Passport, I=ID/PR Card)",
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

            passport_btn.click(
                _load_passport_template,
                inputs=[], outputs=_gen_fields,
            )
            pr_btn.click(
                _load_pr_template,
                inputs=[], outputs=_gen_fields,
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
                " Use the **crop sliders** to isolate"
                " just the MRZ zone (the 2-3 lines of"
                " `<<<` text at the bottom of the"
                " document). Then click Extract."
            )
            with gr.Row():
                with gr.Column():
                    mrz_scan_img = gr.Image(
                        label="Upload Document Image",
                    )
                    gr.Markdown("**Crop (% of image)**")
                    with gr.Row():
                        mrz_crop_top = gr.Slider(
                            minimum=0, maximum=95,
                            value=60, step=5,
                            label="Crop from top %"
                            " (slide right to cut"
                            " more from top)",
                        )
                        mrz_crop_bottom = gr.Slider(
                            minimum=5, maximum=100,
                            value=100, step=5,
                            label="Crop from bottom %"
                            " (slide left to cut"
                            " from bottom)",
                        )
                    mrz_scan_btn = gr.Button(
                        "Extract MRZ from Image",
                        variant="primary",
                    )
                    mrz_crop_preview = gr.Image(
                        label="Cropped Preview"
                        " (this is what OCR sees)",
                    )
                with gr.Column():
                    mrz_scan_text = gr.Textbox(
                        label="Extracted MRZ", lines=4,
                    )
                    mrz_scan_parsed = gr.Textbox(
                        label="Parsed Fields", lines=12,
                    )
                    mrz_scan_status = gr.Textbox(
                        label="Scan Status", lines=2,
                    )
            mrz_scan_btn.click(
                _mrz_scan_image,
                inputs=[
                    mrz_scan_img, mrz_crop_top,
                    mrz_crop_bottom,
                ],
                outputs=[
                    mrz_crop_preview, mrz_scan_text,
                    mrz_scan_parsed, mrz_scan_status,
                ],
            )

            # Fill from scan wiring
            fill_btn.click(
                _mrz_fill_from_scan,
                inputs=[mrz_scan_parsed],
                outputs=_gen_fields + [mrz_gen_status],
            )

            # ── Section 2b: Manual paste ──
            gr.Markdown("---")
            gr.Markdown("### Or paste MRZ text manually")
            with gr.Row():
                mrz_paste_input = gr.Textbox(
                    label="Paste MRZ text here",
                    lines=4,
                    placeholder=(
                        "e.g. CACANPD01830178<111..."
                    ),
                )
                mrz_paste_ocr = gr.Checkbox(
                    label="Apply OCR correction",
                    value=True,
                )
            mrz_paste_btn = gr.Button("Parse & Validate")
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
