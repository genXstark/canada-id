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

    # Province mismatch guard
    mismatches = check_province_match(province_code, fields)
    if mismatches:
        warnings = []
        for m in mismatches:
            icon = "🚫" if m.severity == "error" else "⚠️"
            warnings.append(f"{icon} {m.message}")

        detected, _ = auto_fix_province(fields)
        if detected:
            warnings.append(
                f"\n💡 Auto-fix: Your data belongs to {detected}."
                f" Switch province to '{detected}' or fix your field data."
            )

        return None, "\n".join(warnings), "BLOCKED — province mismatch"

    aamva_string = build_aamva(fields, province_code)
    barcode = encode_pdf417(aamva_string)
    img = barcode_to_image(barcode, scale=3)

    # Log to history
    _db.log_encode(
        province=province_code,
        fields=fields,
        aamva_string=aamva_string,
        barcode_img=img,
    )

    return img, aamva_string, f"✅ Saved (province: {province_code})"


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
            icon = "🚫 MISMATCH" if m.severity == "error" else "⚠️ WARNING"
            lines.append(f"[{icon}] {m.field}: {m.message}")
        lines.append("")

    errors = validate_aamva(fields, province_code)
    if not errors and not mismatches:
        result = "✅ All fields valid."
    else:
        for err in errors:
            icon = "ERROR" if err.severity == "error" else "WARN"
            lines.append(f"[{icon}] {err.field}: {err.message}")
        result = "\n".join(lines) if lines else "✅ All fields valid."

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
            return gr.update(value=choice), f"✅ {reason}"
        except KeyError:
            return gr.update(), f"Unknown province code: {detected}"

    return gr.update(), f"⚠️ {reason}"


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


def create_app() -> gr.Blocks:
    """Create the Gradio application."""
    choices = _province_choices()

    with gr.Blocks(title="Canada ID - AAMVA Barcode Tool") as app:
        gr.Markdown("# 🇨🇦 Canada ID — AAMVA PDF417 Barcode Tool")
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
                            "🔍 Auto-Detect Province",
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
                f"*📊 Lifetime stats: {stats.get('encode', 0)} encodes,"
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
