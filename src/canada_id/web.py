"""Gradio web UI for canada-id barcode encoding and decoding."""
import json

import gradio as gr
from PIL import Image

from canada_id.provinces.registry import all_profiles, get_profile


def _province_choices() -> list[str]:
    """Build province dropdown choices."""
    return [f"{p.code} - {p.name}" for p in all_profiles()]


def _decode_image(image):
    """Decode a PDF417 barcode image and parse AAMVA fields."""
    if image is None:
        return "No image provided.", ""

    from canada_id.aamva.parser import parse_aamva
    from canada_id.codec.decoder import decode_pdf417_text

    pil_image = Image.fromarray(image)
    payloads = decode_pdf417_text(pil_image)

    if not payloads:
        return "No PDF417 barcode found.", ""

    raw = payloads[0]
    fields = parse_aamva(raw)
    table = "\n".join(f"{k}: {v}" for k, v in sorted(fields.items()))
    return table, raw


def _encode_barcode(province_choice, fields_json):
    """Generate a PDF417 barcode from AAMVA field data."""
    if not province_choice or not fields_json:
        return None, "Please select a province and enter field data."

    from canada_id.aamva.builder import build_aamva
    from canada_id.codec.encoder import barcode_to_image, encode_pdf417

    province_code = province_choice.split(" - ")[0].strip()

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"

    aamva_string = build_aamva(fields, province_code)
    barcode = encode_pdf417(aamva_string)
    img = barcode_to_image(barcode, scale=3)
    return img, aamva_string


def _validate_fields(province_choice, fields_json):
    """Validate AAMVA fields against province rules."""
    if not province_choice or not fields_json:
        return "Please select a province and enter field data."

    from canada_id.aamva.validator import validate_aamva

    province_code = province_choice.split(" - ")[0].strip()

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    errors = validate_aamva(fields, province_code)
    if not errors:
        return "All fields valid."

    lines = []
    for err in errors:
        icon = "ERROR" if err.severity == "error" else "WARN"
        lines.append(f"[{icon}] {err.field}: {err.message}")
    return "\n".join(lines)


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


def create_app() -> gr.Blocks:
    """Create the Gradio application."""
    choices = _province_choices()

    with gr.Blocks(title="Canada ID - AAMVA Barcode Tool") as app:
        gr.Markdown("# Canada ID - AAMVA PDF417 Barcode Tool")
        gr.Markdown(
            "Encode and decode AAMVA-standard PDF417 barcodes"
            " for all Canadian provinces and territories."
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
            decode_btn = gr.Button("Decode", variant="primary")
            decode_btn.click(
                _decode_image,
                inputs=[decode_input],
                outputs=[decode_fields, decode_raw],
            )

        with gr.Tab("Encode"):
            gr.Markdown("Generate a PDF417 barcode from AAMVA field data.")
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
                with gr.Column():
                    encode_output = gr.Image(label="Generated Barcode")
                    encode_aamva = gr.Textbox(
                        label="AAMVA String", lines=5,
                    )
                    validate_output = gr.Textbox(
                        label="Validation Result", lines=5,
                    )
            encode_btn.click(
                _encode_barcode,
                inputs=[encode_province, encode_fields],
                outputs=[encode_output, encode_aamva],
            )
            validate_btn.click(
                _validate_fields,
                inputs=[encode_province, encode_fields],
                outputs=[validate_output],
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

    return app


def launch():
    """Launch the Gradio web UI."""
    app = create_app()
    app.launch(share=False)


if __name__ == "__main__":
    launch()
