"""Complete ID Generator - Production Ready.

Generates all Canadian ID types with proper templates, barcodes, and MRZ.
Uses the project's native implementations for all barcode and MRZ generation.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from canada_id.compat.barcode_compat import (
    generate_aamva_data,
    generate_code128,
    generate_pdf417,
)
from canada_id.compat.mrz_compat import (
    convert_date_format,
    generate_passport_mrz,
    generate_pr_card_mrz,
)
from canada_id.templates.generator import (
    generate_passport as template_generate_passport,
    generate_pr_card as template_generate_pr_card,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
TEMPLATE_DIR = "templates"
OUTPUT_DIR = "output"
FONT_DIR = "fonts"

# Default fonts
DEFAULT_FONT = "arial.ttf"
BOLD_FONT = "arialbd.ttf"

# Standard ID card size (3.375" x 2.125" at 254 DPI)
CARD_SIZE = (856, 540)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def load_font(font_name: str, size: int = 20) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, fall back to default if not found."""
    font_paths = [
        os.path.join(FONT_DIR, font_name),
        font_name,
        "arial.ttf",
        "cour.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    
    # Final fallback to default font
    return ImageFont.load_default()


def resize_photo(photo_path: str, target_size: tuple[int, int] = (240, 300)) -> Image.Image:
    """Resize and crop photo to target size.
    
    Args:
        photo_path: Path to photo file
        target_size: (width, height) in pixels
    
    Returns:
        PIL Image object
    """
    photo = Image.open(photo_path)
    
    # Convert to RGB if needed
    if photo.mode != "RGB":
        photo = photo.convert("RGB")
    
    # Calculate aspect ratios
    target_ratio = target_size[0] / target_size[1]
    photo_ratio = photo.width / photo.height
    
    # Crop to match target ratio
    if photo_ratio > target_ratio:
        new_width = int(photo.height * target_ratio)
        left = (photo.width - new_width) // 2
        photo = photo.crop((left, 0, left + new_width, photo.height))
    else:
        new_height = int(photo.width / target_ratio)
        top = (photo.height - new_height) // 2
        photo = photo.crop((0, top, photo.width, top + new_height))
    
    # Resize to exact target size
    photo = photo.resize(target_size, Image.Resampling.LANCZOS)
    
    return photo


def add_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    position: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    color: str = "white",
    align: str = "left",
) -> None:
    """Add text to image with optional alignment.
    
    Args:
        draw: ImageDraw object
        text: Text to add
        position: (x, y) coordinates
        font: ImageFont object
        color: Text color
        align: 'left', 'center', or 'right'
    """
    if align == "center":
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        position = (position[0] - text_width // 2, position[1])
    elif align == "right":
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        position = (position[0] - text_width, position[1])
    
    draw.text(position, text, font=font, fill=color)


# ============================================================================
# ONTARIO DRIVER'S LICENSE
# ============================================================================


def generate_ontario_dl(data: dict) -> tuple[str, str]:
    """Generate Ontario Driver's License (front + back).
    
    Args:
        data: Dictionary with user information
            Required keys:
            - photo: Path to photo file
            - surname: Last name
            - given_names: First and middle names
            - dob: Date of birth (YYYY-MM-DD or YYMMDD)
            - sex: M/F/X
            - height: Height in cm
            - eyes: Eye color code (BRO, BLU, etc.)
            - hair: Hair color code
            - address: Street address
            - city: City
            - province: Province code (ON)
            - postal_code: Postal code
            - license_number: License number
            - issue_date: Issue date (YYYY-MM-DD or YYYYMMDD)
            - expiry_date: Expiry date (YYYY-MM-DD or YYYYMMDD)
    
    Returns:
        tuple: (front_path, back_path)
    """
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Convert dates to proper formats
    dob_yyyymmdd = convert_date_format(data["dob"], "%Y-%m-%d", "%Y%m%d")
    issue_yyyymmdd = convert_date_format(data["issue_date"], "%Y-%m-%d", "%Y%m%d")
    expiry_yyyymmdd = convert_date_format(data["expiry_date"], "%Y-%m-%d", "%Y%m%d")
    
    # ========================================================================
    # FRONT SIDE
    # ========================================================================
    
    # Load template (or create blank if template doesn't exist)
    template_path = os.path.join(TEMPLATE_DIR, "ontario_dl_front.png")
    if os.path.exists(template_path):
        front = Image.open(template_path)
        front = front.resize(CARD_SIZE, Image.Resampling.LANCZOS)
    else:
        # Create with Ontario blue/teal gradient
        front = Image.new("RGB", CARD_SIZE, color="#1E5A7D")
    
    # Resize and paste photo
    photo = resize_photo(data["photo"], target_size=(240, 300))
    front.paste(photo, (50, 120))
    
    # Draw text fields
    draw = ImageDraw.Draw(front)
    font_large = load_font(BOLD_FONT, 28)
    font_medium = load_font(DEFAULT_FONT, 22)
    font_small = load_font(DEFAULT_FONT, 18)
    
    # Header
    add_text(draw, "ONTARIO", (350, 30), font_large, "white")
    add_text(draw, "DRIVER LICENCE / PERMIS DE CONDUIRE", (350, 70), font_small, "white")
    
    # Fields
    y_offset = 140
    add_text(draw, f"SURNAME / NOM: {data['surname'].upper()}", (320, y_offset), font_medium, "white")
    y_offset += 40
    add_text(draw, f"GIVEN NAMES / PRÉNOMS: {data['given_names'].upper()}", (320, y_offset), font_medium, "white")
    y_offset += 40
    add_text(draw, f"ADDRESS / ADRESSE: {data['address'].upper()}", (320, y_offset), font_small, "white")
    y_offset += 30
    add_text(draw, f"{data['city'].upper()}, {data['province'].upper()} {data['postal_code'].upper()}", (320, y_offset), font_small, "white")
    y_offset += 40
    add_text(draw, f"DOB / DN: {data['dob']}", (320, y_offset), font_medium, "white")
    add_text(draw, f"SEX / SEXE: {data['sex'].upper()}", (580, y_offset), font_medium, "white")
    y_offset += 40
    add_text(draw, f"HT: {data['height']} CM", (320, y_offset), font_small, "white")
    add_text(draw, f"EYES / YEUX: {data['eyes'].upper()}", (480, y_offset), font_small, "white")
    y_offset += 40
    add_text(draw, "LICENSE NO / N° DE PERMIS:", (50, y_offset), font_small, "white")
    add_text(draw, data["license_number"], (50, y_offset + 25), font_large, "white")
    
    # Issue and expiry dates
    add_text(draw, f"ISSUED / DÉLIVRÉ: {data['issue_date']}", (320, 450), font_small, "white")
    add_text(draw, f"EXPIRES / EXPIRE: {data['expiry_date']}", (320, 480), font_small, "white")
    
    # Generate and add Code 128 barcode (front side)
    barcode_data = data["license_number"].replace("-", "")[:15]  # Max 15 chars for Code 128
    code128_img = generate_code128(barcode_data, module_width=0.25, module_height=8)
    code128_img = code128_img.resize((300, 60), Image.Resampling.LANCZOS)
    front.paste(code128_img, (520, 450))
    
    # Save front
    front_path = os.path.join(OUTPUT_DIR, f"ontario_dl_front_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    front.save(front_path)
    
    # ========================================================================
    # BACK SIDE
    # ========================================================================
    
    template_back_path = os.path.join(TEMPLATE_DIR, "ontario_dl_back.png")
    if os.path.exists(template_back_path):
        back = Image.open(template_back_path)
    else:
        back = Image.new("RGB", CARD_SIZE, color="#F5F5F5")
    
    # Generate AAMVA data
    aamva_data = generate_aamva_data(
        province="ON",
        license_number=data["license_number"],
        surname=data["surname"],
        given_names=data["given_names"],
        dob=dob_yyyymmdd,
        issue_date=issue_yyyymmdd,
        expiry_date=expiry_yyyymmdd,
        address=data["address"],
        city=data["city"],
        postal_code=data["postal_code"],
        sex=data["sex"],
        height=data["height"],
        eyes=data["eyes"],
        hair=data.get("hair", "BRO"),
    )
    
    # Generate PDF417 barcode
    pdf417_img = generate_pdf417(aamva_data, scale=2, ratio=3, columns=8)
    
    # Resize PDF417 to fit card
    pdf417_width = min(pdf417_img.width, 600)
    pdf417_height = int(pdf417_img.height * (pdf417_width / pdf417_img.width))
    pdf417_img = pdf417_img.resize((pdf417_width, pdf417_height), Image.Resampling.LANCZOS)
    
    # Center PDF417 on back
    pdf417_x = (CARD_SIZE[0] - pdf417_width) // 2
    pdf417_y = (CARD_SIZE[1] - pdf417_height) // 2
    back.paste(pdf417_img, (pdf417_x, pdf417_y))
    
    # Add text
    draw_back = ImageDraw.Draw(back)
    add_text(draw_back, "ONTARIO DRIVER LICENCE", (CARD_SIZE[0] // 2, 50), font_large, "black", align="center")
    add_text(draw_back, data["license_number"], (CARD_SIZE[0] // 2, 90), font_medium, "black", align="center")
    
    # Save back
    back_path = os.path.join(OUTPUT_DIR, f"ontario_dl_back_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    back.save(back_path)
    
    return (front_path, back_path)


# ============================================================================
# QUEBEC DRIVER'S LICENSE
# ============================================================================


def generate_quebec_dl(data: dict) -> tuple[str, str]:
    """Generate Quebec Driver's License (front + back)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Convert dates
    dob_yyyymmdd = convert_date_format(data["dob"], "%Y-%m-%d", "%Y%m%d")
    issue_yyyymmdd = convert_date_format(data["issue_date"], "%Y-%m-%d", "%Y%m%d")
    expiry_yyyymmdd = convert_date_format(data["expiry_date"], "%Y-%m-%d", "%Y%m%d")
    
    # FRONT
    front = Image.new("RGB", CARD_SIZE, color="#1E5A96")  # Quebec blue
    photo = resize_photo(data["photo"], (240, 300))
    front.paste(photo, (50, 120))
    
    draw = ImageDraw.Draw(front)
    font_large = load_font(BOLD_FONT, 28)
    font_medium = load_font(DEFAULT_FONT, 22)
    
    add_text(draw, "QUÉBEC", (350, 30), font_large, "white")
    add_text(draw, "PERMIS DE CONDUIRE", (350, 70), font_medium, "white")
    add_text(draw, f"{data['surname'].upper()}, {data['given_names'].upper()}", (320, 140), font_medium, "white")
    add_text(draw, f"NÉ(E) LE: {data['dob']}", (320, 180), font_medium, "white")
    add_text(draw, f"NO: {data['license_number']}", (320, 220), font_large, "white")
    
    front_path = os.path.join(OUTPUT_DIR, f"quebec_dl_front_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    front.save(front_path)
    
    # BACK with PDF417
    back = Image.new("RGB", CARD_SIZE, color="#F5F5F5")
    
    aamva_data = generate_aamva_data(
        province="QC",
        license_number=data["license_number"],
        surname=data["surname"],
        given_names=data["given_names"],
        dob=dob_yyyymmdd,
        issue_date=issue_yyyymmdd,
        expiry_date=expiry_yyyymmdd,
        address=data["address"],
        city=data["city"],
        postal_code=data["postal_code"],
        sex=data["sex"],
        height=data["height"],
        eyes=data["eyes"],
        hair=data.get("hair", "BRO"),
    )
    
    pdf417_img = generate_pdf417(aamva_data, scale=2)
    pdf417_width = min(pdf417_img.width, 600)
    pdf417_height = int(pdf417_img.height * (pdf417_width / pdf417_img.width))
    pdf417_img = pdf417_img.resize((pdf417_width, pdf417_height), Image.Resampling.LANCZOS)
    
    pdf417_x = (CARD_SIZE[0] - pdf417_width) // 2
    pdf417_y = (CARD_SIZE[1] - pdf417_height) // 2
    back.paste(pdf417_img, (pdf417_x, pdf417_y))
    
    back_path = os.path.join(OUTPUT_DIR, f"quebec_dl_back_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    back.save(back_path)
    
    return (front_path, back_path)


# ============================================================================
# CANADIAN PASSPORT
# ============================================================================


def generate_passport(data: dict) -> str:
    """Generate Canadian Passport data page.
    
    Args:
        data: Dictionary with:
            - photo: Path to photo file
            - surname: Last name
            - given_names: First and middle names
            - passport_number: Passport number
            - dob: Date of birth (YYYY-MM-DD)
            - sex: M/F/X
            - issue_date: Issue date
            - expiry_date: Expiry date
            - place_of_birth: City of birth
    
    Returns:
        str: Path to generated passport image
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    dob_yymmdd = convert_date_format(data["dob"], "%Y-%m-%d", "%y%m%d")
    expiry_yymmdd = convert_date_format(data["expiry_date"], "%Y-%m-%d", "%y%m%d")
    issue_yymmdd = convert_date_format(data["issue_date"], "%Y-%m-%d", "%y%m%d")

    fields = {
        "document_type": "P",
        "country_code": "CAN",
        "document_number": data["passport_number"],
        "passport_no": data["passport_number"],
        "surname": data["surname"],
        "given_names": data["given_names"],
        "nationality": "CAN",
        "date_of_birth": dob_yymmdd,
        "sex": data["sex"],
        "expiry_date": expiry_yymmdd,
        "date_of_issue": issue_yymmdd,
        "place_of_birth": data.get("place_of_birth", "CANADA"),
    }
    photo = Image.open(data["photo"]).convert("RGB")
    generated = template_generate_passport(fields, photo=photo)

    passport_path = os.path.join(OUTPUT_DIR, f"passport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    generated.image.save(passport_path)
    return passport_path


# ============================================================================
# PR CARD
# ============================================================================


def generate_pr_card(data: dict) -> tuple[str, str]:
    """Generate Permanent Resident Card (front and back).
    
    Args:
        data: Dictionary with:
            - photo: Path to photo file
            - surname: Last name
            - given_names: First and middle names
            - pr_number: PR card number
            - dob: Date of birth
            - sex: M/F/X
            - issue_date: Issue date
            - expiry_date: Expiry date
    
    Returns:
        tuple[str, str]: (front_path, back_path) of generated PR card images
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    dob_yymmdd = convert_date_format(data["dob"], "%Y-%m-%d", "%y%m%d")
    expiry_yymmdd = convert_date_format(data["expiry_date"], "%Y-%m-%d", "%y%m%d")
    fields = {
        "document_type": "I",
        "country_code": "CAN",
        "document_number": data["pr_number"][:9],
        "surname": data["surname"],
        "given_names": data["given_names"],
        "nationality": "CAN",
        "date_of_birth": dob_yymmdd,
        "sex": data["sex"],
        "expiry_date": expiry_yymmdd,
        "country_of_birth": data.get("place_of_birth", "CANADA"),
        "pr_number": data["pr_number"],
        "optional_data_1": data["pr_number"][:9],
    }

    photo = Image.open(data["photo"]).convert("RGB")
    generated = template_generate_pr_card(fields, photo=photo)
    front_path = os.path.join(OUTPUT_DIR, f"pr_card_front_{timestamp}.png")
    generated.image.save(front_path)

    # Keep legacy two-file contract by producing a back side with MRZ block.
    back_img = Image.new("RGB", generated.image.size, color="#F5F5F5")
    draw_back = ImageDraw.Draw(back_img)
    font_medium = load_font(DEFAULT_FONT, 22)
    font_small = load_font(DEFAULT_FONT, 16)
    font_mrz = load_font("cour.ttf", 20)
    add_text(draw_back, "PERMANENT RESIDENT CARD", (30, 30), font_medium, "#2E4B5E")
    add_text(draw_back, "CARTE DE RÉSIDENT PERMANENT", (30, 60), font_small, "#2E4B5E")

    mrz = generated.mrz_string or generate_pr_card_mrz(
        surname=data["surname"],
        given_names=data["given_names"],
        pr_number=data["pr_number"],
        dob=dob_yymmdd,
        sex=data["sex"],
        expiry_date=expiry_yymmdd,
    )
    mrz_lines = mrz.split("\n")
    mrz_y = generated.image.height - 180
    for line in mrz_lines:
        add_text(draw_back, line, (40, mrz_y), font_mrz, "black")
        mrz_y += 44

    back_path = os.path.join(OUTPUT_DIR, f"pr_card_back_{timestamp}.png")
    back_img.save(back_path)
    return (front_path, back_path)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CANADA ID GENERATOR - TEST SUITE")
    print("Using native project implementations")
    print("=" * 60)
    
    # Create a simple test photo if none exists
    test_photo = os.path.join(OUTPUT_DIR, "test_photo.png")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(test_photo):
        # Create placeholder photo
        photo_img = Image.new("RGB", (300, 400), color="#C0C0C0")
        draw = ImageDraw.Draw(photo_img)
        draw.text((100, 180), "PHOTO", fill="black")
        photo_img.save(test_photo)
        print(f"Created test photo: {test_photo}")
    
    # Test data
    test_person = {
        "photo": test_photo,
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "dob": "1995-05-23",
        "sex": "M",
        "height": "175",
        "eyes": "BRO",
        "hair": "BRO",
        "address": "123 Main Street",
        "city": "Toronto",
        "province": "ON",
        "postal_code": "M5H 2N2",
        "license_number": "S1234-56789-01234",
        "issue_date": "2024-01-15",
        "expiry_date": "2029-05-23",
        "passport_number": "AB123456",
        "pr_number": "1234567890",
        "place_of_birth": "Toronto",
    }
    
    print("\n1. ONTARIO DRIVER'S LICENSE")
    print("-" * 60)
    try:
        front, back = generate_ontario_dl(test_person)
        print(f"✅ Front: {front}")
        print(f"✅ Back: {back}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n2. QUEBEC DRIVER'S LICENSE")
    print("-" * 60)
    try:
        qc_data = test_person.copy()
        qc_data["province"] = "QC"
        qc_data["license_number"] = "D1234-567890-12"
        front, back = generate_quebec_dl(qc_data)
        print(f"✅ Front: {front}")
        print(f"✅ Back: {back}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n3. CANADIAN PASSPORT")
    print("-" * 60)
    try:
        passport_path = generate_passport(test_person)
        print(f"✅ Passport: {passport_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n4. PR CARD")
    print("-" * 60)
    try:
        front, back = generate_pr_card(test_person)
        print(f"✅ PR Card Front: {front}")
        print(f"✅ PR Card Back: {back}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print(f"Check the '{OUTPUT_DIR}/' folder for generated images.")
    print("=" * 60)
