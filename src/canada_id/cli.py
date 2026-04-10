"""CLI interface for canada-id barcode operations."""
import json
import sys

import click
from PIL import Image

from canada_id.provinces.registry import all_profiles, get_profile

PROVINCE_CODES = [p.code for p in all_profiles()]


@click.group()
@click.version_option(package_name="canada-id")
def main():
    """Canadian AAMVA PDF417 barcode toolkit."""


@main.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text", "raw"]),
    default="text",
    help="Output format.",
)
@click.option("--parse/--no-parse", default=True, help="Parse AAMVA fields.")
def decode(image_path: str, output_format: str, parse: bool):
    """Decode a PDF417 barcode image."""
    from canada_id.aamva.parser import parse_aamva
    from canada_id.codec.decoder import decode_pdf417_text

    image = Image.open(image_path)
    payloads = decode_pdf417_text(image)

    if not payloads:
        click.echo("No PDF417 barcode found.", err=True)
        sys.exit(1)

    for i, payload in enumerate(payloads):
        if len(payloads) > 1:
            click.echo(f"--- Barcode {i + 1} ---")

        if parse:
            fields = parse_aamva(payload)
            _output_fields(fields, output_format)
        else:
            click.echo(payload)


def _output_fields(fields: dict[str, str], fmt: str):
    """Print parsed fields in the requested format."""
    if fmt == "json":
        click.echo(json.dumps(fields, indent=2))
    elif fmt == "text":
        for key, val in sorted(fields.items()):
            click.echo(f"{key}: {val}")
    else:
        for val in fields.values():
            click.echo(val)


@main.command()
@click.option(
    "--province",
    required=True,
    type=click.Choice(PROVINCE_CODES, case_sensitive=False),
    help="Province/territory code.",
)
@click.option(
    "--fields",
    "fields_path",
    type=click.Path(exists=True),
    required=True,
    help="JSON file with AAMVA field values.",
)
@click.option("--output", "-o", required=True, help="Output PNG path.")
@click.option("--scale", default=2, help="Barcode scale factor.")
def encode(province: str, fields_path: str, output: str, scale: int):
    """Generate a PDF417 barcode from AAMVA field data."""
    from canada_id.aamva.builder import build_aamva
    from canada_id.codec.encoder import barcode_to_image, encode_pdf417

    with open(fields_path) as f:
        fields = json.load(f)

    aamva_string = build_aamva(fields, province.upper())
    barcode = encode_pdf417(aamva_string)
    img = barcode_to_image(barcode, scale=scale)
    img.save(output)
    click.echo(f"Barcode saved to {output}")


@main.command()
@click.option(
    "--province",
    required=True,
    type=click.Choice(PROVINCE_CODES, case_sensitive=False),
)
@click.option(
    "--fields",
    "fields_path",
    type=click.Path(exists=True),
    required=True,
)
def validate(province: str, fields_path: str):
    """Validate AAMVA field data against province rules."""
    from canada_id.aamva.validator import validate_aamva

    with open(fields_path) as f:
        fields = json.load(f)

    errors = validate_aamva(fields, province.upper())
    if not errors:
        click.echo("All fields valid.")
        return

    for err in errors:
        icon = "ERROR" if err.severity == "error" else "WARN"
        click.echo(f"[{icon}] {err.field}: {err.message}")

    error_count = sum(1 for e in errors if e.severity == "error")
    if error_count > 0:
        sys.exit(1)


@main.command()
@click.option(
    "--province",
    required=True,
    type=click.Choice(PROVINCE_CODES, case_sensitive=False),
)
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True),
    required=True,
    help="Card template image.",
)
@click.option(
    "--fields",
    "fields_path",
    type=click.Path(exists=True),
    required=True,
)
@click.option("--output", "-o", required=True, help="Output image path.")
def composite(
    province: str,
    template_path: str,
    fields_path: str,
    output: str,
):
    """Composite a barcode onto a card template."""
    from canada_id.aamva.builder import build_aamva
    from canada_id.card.compositor import composite_barcode_on_card
    from canada_id.card.layout import BarcodeRegion
    from canada_id.codec.encoder import barcode_to_image, encode_pdf417

    with open(fields_path) as f:
        fields = json.load(f)

    profile = get_profile(province.upper())
    aamva_string = build_aamva(fields, province.upper())
    barcode = encode_pdf417(aamva_string)
    barcode_img = barcode_to_image(barcode, scale=3)

    card_img = Image.open(template_path)
    region = BarcodeRegion(
        x_frac=0.02, y_frac=0.05, w_frac=0.37,
        h_frac=0.90, rotation_deg=-90.0,
    )

    result = composite_barcode_on_card(card_img, barcode_img, region)
    result.save(output)
    click.echo(f"Composite saved to {output}")


@main.command()
@click.option(
    "--province",
    type=click.Choice(PROVINCE_CODES, case_sensitive=False),
    help="Filter by province.",
)
def provinces(province: str | None):
    """List province profiles and their details."""
    profiles = [get_profile(province)] if province else all_profiles()
    for p in profiles:
        click.echo(f"{p.code} | {p.name} | IIN: {p.iin} | v{p.aamva_version}")
        if province:
            click.echo(f"  Date format: {p.date_format}")
            click.echo(f"  Height unit: {p.height_unit}")
            classes = ", ".join(
                f"{k}={v}" for k, v in p.vehicle_classes.items()
            )
            click.echo(f"  Vehicle classes: {classes}")


@main.command()
@click.option(
    "--fields",
    "fields_path",
    type=click.Path(exists=True),
    help="JSON file with AAMVA field values (auto-converts to MRZ).",
)
@click.option(
    "--format",
    "mrz_format",
    type=click.Choice(["TD1", "TD2", "TD3"]),
    default="TD1",
    help="MRZ format type.",
)
@click.option("--output", "-o", help="Save MRZ image to file.")
def mrz(fields_path: str | None, mrz_format: str, output: str | None):
    """Generate MRZ (Machine Readable Zone) from AAMVA data."""
    from canada_id.mrz.aamva_bridge import aamva_to_mrz_data
    from canada_id.mrz.generator import generate_mrz
    from canada_id.mrz.renderer import render_mrz_image

    if fields_path:
        with open(fields_path) as f:
            fields = json.load(f)
        mrz_data = aamva_to_mrz_data(fields)
    else:
        click.echo("Provide --fields with AAMVA JSON data.", err=True)
        sys.exit(1)

    mrz_string = generate_mrz(mrz_data, mrz_format)
    click.echo(mrz_string)

    if output:
        img = render_mrz_image(mrz_string, scale=3)
        img.save(output)
        click.echo(f"MRZ image saved to {output}")


@main.command()
@click.argument("mrz_text")
@click.option(
    "--ocr-correct/--no-ocr-correct",
    default=False,
    help="Apply OCR error correction.",
)
def parse_mrz_cmd(mrz_text: str, ocr_correct: bool):
    """Parse and validate an MRZ string (Canada-only)."""
    from canada_id.mrz.parsers import MrzParseError, parse_mrz

    mrz_text = mrz_text.replace("\\n", "\n")
    try:
        result = parse_mrz(
            mrz_text, ocr_correct=ocr_correct, canada_only=True,
        )
    except (MrzParseError, ValueError) as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Format: {result.format.value}")
    click.echo(f"Check digits valid: {result.check_digits_valid}")
    click.echo(f"Document Type: {result.document_type}")
    click.echo(f"Country: {result.issuing_country}")
    click.echo(f"Name: {result.surname}, {result.given_names}")
    click.echo(f"Doc Number: {result.document_number}")
    click.echo(f"Nationality: {result.nationality}")
    click.echo(f"DOB: {result.date_of_birth}")
    click.echo(f"Sex: {result.sex.value}")
    click.echo(f"Expiry: {result.expiry_date}")
    if result.optional_data_1:
        click.echo(f"Optional 1: {result.optional_data_1}")
    if result.optional_data_2:
        click.echo(f"Optional 2: {result.optional_data_2}")
    if result.personal_number:
        click.echo(f"Personal Number: {result.personal_number}")


if __name__ == "__main__":
    main()
