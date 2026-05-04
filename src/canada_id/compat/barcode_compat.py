"""Barcode generator compatibility layer.

Provides the same API as barcode_generator_complete.py
but uses the project's native implementations.
"""
from __future__ import annotations

from PIL import Image

from canada_id.aamva.builder import build_aamva
from canada_id.codec.code128 import code128_to_image
from canada_id.codec.code39 import code39_to_image
from canada_id.codec.encoder import barcode_to_image, encode_pdf417


def generate_pdf417(
    data: str,
    scale: int = 3,
    ratio: int = 3,
    columns: int = 10,
) -> Image.Image:
    """Generate PDF417 2D barcode (used on back of driver's licenses).
    
    Args:
        data: AAMVA-formatted data string
        scale: Barcode module width in pixels (default: 3)
        ratio: Height to width ratio (default: 3) - currently not used
        columns: Number of data columns (default: 10) - currently not used
    
    Returns:
        PIL Image object
    
    Example:
        >>> data = generate_aamva_data(...)
        >>> barcode_img = generate_pdf417(data)
        >>> barcode_img.save("dl_back_barcode.png")
    """
    # Use native encoder
    barcode = encode_pdf417(data)
    if not barcode:
        # Return blank image if encoding fails
        return Image.new("L", (100, 50), 255)
    return barcode_to_image(barcode, scale=scale)


def generate_code128(
    data: str,
    module_width: float = 0.3,
    module_height: float = 10,
) -> Image.Image:
    """Generate Code 128 linear barcode.
    
    Args:
        data: Data to encode (usually license number)
        module_width: Bar width in mm (default: 0.3)
        module_height: Bar height in mm (default: 10)
    
    Returns:
        PIL Image object
    
    Example:
        >>> barcode = generate_code128("S1234567890123")
        >>> barcode.save("license_barcode.png")
    """
    # Convert mm to pixels (assuming ~3 pixels per mm)
    width_px = max(1, int(module_width * 3))
    height_px = max(20, int(module_height * 4))
    
    return code128_to_image(
        data,
        module_width=width_px,
        bar_height=height_px,
        show_text=False,
    )


def generate_code39(
    data: str,
    module_width: float = 0.3,
    module_height: float = 10,
) -> Image.Image:
    """Generate Code 39 linear barcode.
    
    Args:
        data: Data to encode
        module_width: Bar width in mm
        module_height: Bar height in mm
    
    Returns:
        PIL Image object
    """
    narrow = max(1, int(module_width * 3))
    wide = narrow * 3
    height_px = max(20, int(module_height * 4))
    
    return code39_to_image(
        data,
        narrow=narrow,
        wide=wide,
        bar_height=height_px,
    )


def generate_qr_code(
    data: str,
    box_size: int = 10,
    border: int = 4,
) -> Image.Image:
    """Generate QR code (optional, some IDs use it).
    
    Note: Requires qrcode package. Falls back to placeholder
    if not available.
    
    Args:
        data: Data to encode
        box_size: Size of each box in pixels
        border: Border size in boxes
    
    Returns:
        PIL Image object
    """
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")
    except ImportError:
        # Return placeholder if qrcode not installed
        size = (box_size * 21, box_size * 21)
        img = Image.new("L", size, 255)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((size[0]//4, size[1]//2), "QR", fill=0)
        return img


def generate_aamva_data(
    province: str,
    license_number: str,
    surname: str,
    given_names: str,
    dob: str,
    issue_date: str,
    expiry_date: str,
    address: str,
    city: str,
    postal_code: str,
    sex: str,
    height: str,
    eyes: str,
    hair: str = "",
) -> str:
    """Generate AAMVA-compliant data string for PDF417 barcode.
    
    AAMVA = American Association of Motor Vehicle Administrators
    Standard format used by all North American driver's licenses.
    
    Args:
        province: Province code (ON, QC, BC, AB, etc.)
        license_number: Driver's license number
        surname: Last name
        given_names: First and middle names
        dob: Date of birth (YYYYMMDD format)
        issue_date: Issue date (YYYYMMDD format)
        expiry_date: Expiry date (YYYYMMDD format)
        address: Street address
        city: City
        postal_code: Postal code
        sex: Sex (M/F/X)
        height: Height in cm (e.g., "175")
        eyes: Eye color code (BLU, BRO, GRN, GRY, HAZ, BLK)
        hair: Hair color code (optional)
    
    Returns:
        str: AAMVA-formatted data string
    
    AAMVA Data Elements:
        DCS = Last name
        DCT = First name + middle name
        DBB = Date of birth
        DBA = Expiry date
        DBD = Issue date
        DAQ = License number
        DAG = Street address
        DAI = City
        DAJ = Province/State
        DAK = Postal code
        DAU = Height
        DAY = Eye color
        DAZ = Hair color
        DBC = Sex
        DCF = Document discriminator
        DCG = Issue country
    """
    # Build fields dictionary for the AAMVA builder
    fields = {
        "DCS": surname.upper(),
        "DCT": given_names.upper(),
        "DBB": dob,
        "DBA": expiry_date,
        "DBD": issue_date,
        "DAQ": license_number,
        "DAG": address.upper(),
        "DAI": city.upper(),
        "DAJ": province.upper(),
        "DAK": postal_code.upper().replace(" ", ""),
        "DAU": f"{height} CM",
        "DAY": eyes.upper(),
        "DBC": "1" if sex.upper() == "M" else "2" if sex.upper() == "F" else "9",
        "DCG": "CAN",
        "DCD": "NONE",
    }
    
    if hair:
        fields["DAZ"] = hair.upper()
    
    # Use native AAMVA builder
    return build_aamva(fields, province.upper())


# For backwards compatibility with the original script
if __name__ == "__main__":
    import os
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    print("=" * 60)
    print("BARCODE GENERATOR TEST")
    print("=" * 60)
    
    # Test 1: AAMVA data generation
    print("\n1. AAMVA DATA GENERATION")
    print("-" * 60)
    aamva_data = generate_aamva_data(
        province="ON",
        license_number="S1234-56789-01234",
        surname="SMITH",
        given_names="JOHN ALEXANDER",
        dob="19950523",
        issue_date="20201023",
        expiry_date="20281023",
        address="123 MAIN STREET",
        city="TORONTO",
        postal_code="M5H 2N2",
        sex="M",
        height="175",
        eyes="BRO",
        hair="BRO",
    )
    print("AAMVA Data (first 200 chars):")
    print(aamva_data[:200] + "...")
    print(f"Total length: {len(aamva_data)} bytes")
    
    # Test 2: PDF417 generation
    print("\n2. PDF417 BARCODE (AAMVA)")
    print("-" * 60)
    pdf417_image = generate_pdf417(aamva_data, scale=3, ratio=3, columns=10)
    pdf417_path = "output/test_pdf417_aamva.png"
    pdf417_image.save(pdf417_path)
    print(f"✅ Saved: {pdf417_path}")
    print(f"   Size: {pdf417_image.size}")
    
    # Test 3: Code 128 generation
    print("\n3. CODE 128 BARCODE (License Number)")
    print("-" * 60)
    code128_image = generate_code128("S123456789012", module_width=0.3, module_height=10)
    code128_path = "output/test_code128.png"
    code128_image.save(code128_path)
    print(f"✅ Saved: {code128_path}")
    print(f"   Size: {code128_image.size}")
    
    # Test 4: Code 39 generation
    print("\n4. CODE 39 BARCODE")
    print("-" * 60)
    code39_image = generate_code39("SMITH123", module_width=0.3, module_height=10)
    code39_path = "output/test_code39.png"
    code39_image.save(code39_path)
    print(f"✅ Saved: {code39_path}")
    print(f"   Size: {code39_image.size}")
    
    # Test 5: QR Code generation
    print("\n5. QR CODE")
    print("-" * 60)
    qr_image = generate_qr_code("https://example.com/verify/S123456789012")
    qr_path = "output/test_qr.png"
    qr_image.save(qr_path)
    print(f"✅ Saved: {qr_path}")
    print(f"   Size: {qr_image.size}")
    
    print("\n" + "=" * 60)
    print("ALL BARCODE TESTS COMPLETE")
    print("=" * 60)
