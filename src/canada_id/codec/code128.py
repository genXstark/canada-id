"""Code 128 barcode encoder with check digit calculation.

Supports Code 128 A, B, and C modes with automatic mode selection.
Produces scannable barcodes compliant with ISO/IEC 15417.

Canadian passports use Code 128 for certain elements on the
data page, and some provincial health cards use Code 128.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

# Code 128 character patterns (bar/space widths, 11 modules each)
# Format: BSBSBS (bars and spaces in sequence)
CODE128_PATTERNS: list[str] = [
    "212222",  # 0
    "222122",  # 1
    "222221",  # 2
    "121223",  # 3
    "121322",  # 4
    "131222",  # 5
    "122213",  # 6
    "122312",  # 7
    "132212",  # 8
    "221213",  # 9
    "221312",  # 10
    "231212",  # 11
    "112232",  # 12
    "122132",  # 13
    "122231",  # 14
    "113222",  # 15
    "123122",  # 16
    "123221",  # 17
    "223211",  # 18
    "221132",  # 19
    "221231",  # 20
    "213212",  # 21
    "223112",  # 22
    "312131",  # 23
    "311222",  # 24
    "321122",  # 25
    "321221",  # 26
    "312212",  # 27
    "322112",  # 28
    "322211",  # 29
    "212123",  # 30
    "212321",  # 31
    "232121",  # 32
    "111323",  # 33
    "131123",  # 34
    "131321",  # 35
    "112313",  # 36
    "132113",  # 37
    "132311",  # 38
    "211313",  # 39
    "231113",  # 40
    "231311",  # 41
    "112133",  # 42
    "112331",  # 43
    "132131",  # 44
    "113123",  # 45
    "113321",  # 46
    "133121",  # 47
    "313121",  # 48
    "211331",  # 49
    "231131",  # 50
    "213113",  # 51
    "213311",  # 52
    "213131",  # 53
    "311123",  # 54
    "311321",  # 55
    "331121",  # 56
    "312113",  # 57
    "312311",  # 58
    "332111",  # 59
    "314111",  # 60
    "221411",  # 61
    "431111",  # 62
    "111224",  # 63
    "111422",  # 64
    "121124",  # 65
    "121421",  # 66
    "141122",  # 67
    "141221",  # 68
    "112214",  # 69
    "112412",  # 70
    "122114",  # 71
    "122411",  # 72
    "142112",  # 73
    "142211",  # 74
    "241211",  # 75
    "221114",  # 76
    "413111",  # 77
    "241112",  # 78
    "134111",  # 79
    "111242",  # 80
    "121142",  # 81
    "121241",  # 82
    "114212",  # 83
    "124112",  # 84
    "124211",  # 85
    "411212",  # 86
    "421112",  # 87
    "421211",  # 88
    "212141",  # 89
    "214121",  # 90
    "412121",  # 91
    "111143",  # 92
    "111341",  # 93
    "131141",  # 94
    "114113",  # 95
    "114311",  # 96
    "411113",  # 97
    "411311",  # 98
    "113141",  # 99
    "114131",  # 100
    "311141",  # 101
    "411131",  # 102
    "211412",  # 103: START A
    "211214",  # 104: START B
    "211232",  # 105: START C
    "2331112",  # 106: STOP (13 modules)
]

# Special characters
START_A = 103
START_B = 104
START_C = 105
STOP = 106
CODE_A = 101  # Switch to Code A
CODE_B = 100  # Switch to Code B
CODE_C = 99   # Switch to Code C
FNC1 = 102    # Function 1


def _char_to_value_a(char: str) -> int:
    """Convert character to Code 128 A value."""
    code = ord(char)
    if code < 32:
        return code + 64
    if 32 <= code <= 95:
        return code - 32
    raise ValueError(f"Character {char!r} not in Code 128 A")


def _char_to_value_b(char: str) -> int:
    """Convert character to Code 128 B value."""
    code = ord(char)
    if 32 <= code <= 127:
        return code - 32
    raise ValueError(f"Character {char!r} not in Code 128 B")


def _is_all_digits(text: str) -> bool:
    """Check if text contains only digits."""
    return all(c.isdigit() for c in text)


def _select_mode(text: str) -> str:
    """Select optimal Code 128 mode based on content.
    
    Uses Code C for pure digit sequences (2 digits per symbol),
    Code B for general ASCII, Code A for control characters.
    """
    if not text:
        return "B"
    
    # Code C is most efficient for pure numeric data
    if len(text) >= 4 and _is_all_digits(text) and len(text) % 2 == 0:
        return "C"
    
    # Check for control characters (need Code A)
    for ch in text:
        if ord(ch) < 32:
            return "A"
    
    return "B"


def _encode_data(text: str) -> list[int]:
    """Encode text into Code 128 values with optimal mode switching.
    
    Returns list of symbol values (not including check digit or stop).
    """
    if not text:
        return [START_B]
    
    values: list[int] = []
    mode = _select_mode(text)
    
    # Start character
    if mode == "A":
        values.append(START_A)
    elif mode == "B":
        values.append(START_B)
    else:
        values.append(START_C)
    
    i = 0
    while i < len(text):
        if mode == "C":
            # Code C: encode digit pairs
            if i + 1 < len(text) and text[i].isdigit() and text[i + 1].isdigit():
                values.append(int(text[i:i + 2]))
                i += 2
            else:
                # Switch to B for non-digit
                values.append(CODE_B)
                mode = "B"
        elif mode == "B":
            # Check if we should switch to C for digit runs
            remaining = text[i:]
            digit_run = 0
            for ch in remaining:
                if ch.isdigit():
                    digit_run += 1
                else:
                    break
            
            if digit_run >= 4 and digit_run % 2 == 0:
                values.append(CODE_C)
                mode = "C"
            else:
                values.append(_char_to_value_b(text[i]))
                i += 1
        else:  # mode == "A"
            # Check for mode switch opportunity
            if text[i].isdigit() and i + 3 < len(text):
                remaining = text[i:]
                if _is_all_digits(remaining[:4]) and len(remaining) >= 4:
                    values.append(CODE_C)
                    mode = "C"
                    continue
            
            values.append(_char_to_value_a(text[i]))
            i += 1
    
    return values


def _calculate_checksum(values: list[int]) -> int:
    """Calculate Code 128 check digit.
    
    Checksum = (start_value + sum(position * value)) % 103
    """
    total = values[0]  # Start character weight is position 0, value 1×
    for i, val in enumerate(values[1:], start=1):
        total += i * val
    return total % 103


def encode_code128(
    text: str,
    add_fnc1: bool = False,
) -> list[list[int]]:
    """Encode text as Code 128 barcode.
    
    Args:
        text: Text to encode (ASCII printable characters).
        add_fnc1: Add FNC1 character for GS1-128 compliance.
    
    Returns:
        2D bit array (list of rows, each row is list of 0/1).
        
    Raises:
        ValueError: If text contains invalid characters.
    """
    if not text:
        raise ValueError("Cannot encode empty text")
    
    values = _encode_data(text)
    
    if add_fnc1:
        # Insert FNC1 after start character for GS1-128
        values.insert(1, FNC1)
    
    checksum = _calculate_checksum(values)
    values.append(checksum)
    values.append(STOP)
    
    # Convert values to bar patterns
    bits: list[int] = []
    
    # Quiet zone (10 modules)
    bits.extend([0] * 10)
    
    for val in values:
        pattern = CODE128_PATTERNS[val]
        bar = True  # Start with bar
        for width_char in pattern:
            width = int(width_char)
            bits.extend([1 if bar else 0] * width)
            bar = not bar
    
    # Quiet zone (10 modules)
    bits.extend([0] * 10)
    
    return [bits]


def code128_to_image(
    text: str,
    module_width: int = 2,
    bar_height: int = 80,
    show_text: bool = True,
    text_margin: int = 5,
    add_fnc1: bool = False,
    background: str = "white",
    foreground: str = "black",
) -> Image.Image:
    """Generate Code 128 barcode as PIL Image.
    
    Args:
        text: Text to encode.
        module_width: Width of narrowest bar in pixels.
        bar_height: Height of bars in pixels.
        show_text: Show human-readable text below barcode.
        text_margin: Margin between barcode and text.
        add_fnc1: Add FNC1 for GS1-128 compliance.
        background: Background color.
        foreground: Bar/text color.
    
    Returns:
        PIL Image of the barcode.
        
    Raises:
        ValueError: If text contains invalid characters.
    """
    barcode = encode_code128(text, add_fnc1=add_fnc1)
    bits = barcode[0]
    
    width = len(bits) * module_width
    
    # Calculate text height if showing
    text_height = 0
    if show_text:
        text_height = 14 + text_margin
    
    height = bar_height + text_height
    
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)
    
    # Draw bars
    x = 0
    for bit in bits:
        if bit:
            draw.rectangle(
                [x, 0, x + module_width - 1, bar_height - 1],
                fill=foreground,
            )
        x += module_width
    
    # Draw human-readable text
    if show_text:
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except OSError:
            try:
                font = ImageFont.truetype("cour.ttf", 12)
            except OSError:
                font = ImageFont.load_default()
        
        # Get text bbox for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        text_y = bar_height + text_margin
        
        draw.text((text_x, text_y), text, fill=foreground, font=font)
    
    return img


def encode_gs1_128(data: str) -> list[list[int]]:
    """Encode GS1-128 (EAN-128) barcode.
    
    GS1-128 is Code 128 with FNC1 as the first character,
    used for supply chain applications.
    
    Args:
        data: Application identifier + data string.
        
    Returns:
        2D bit array.
    """
    return encode_code128(data, add_fnc1=True)


def gs1_128_to_image(
    data: str,
    module_width: int = 2,
    bar_height: int = 80,
) -> Image.Image:
    """Generate GS1-128 barcode as PIL Image.
    
    Args:
        data: Application identifier + data string.
        module_width: Width of narrowest bar in pixels.
        bar_height: Height of bars in pixels.
        
    Returns:
        PIL Image of the barcode.
    """
    return code128_to_image(
        data,
        module_width=module_width,
        bar_height=bar_height,
        add_fnc1=True,
    )


def validate_code128_text(text: str) -> tuple[bool, str]:
    """Validate text for Code 128 encoding.
    
    Args:
        text: Text to validate.
        
    Returns:
        Tuple of (is_valid, message).
    """
    if not text:
        return False, "Empty text cannot be encoded"
    
    for i, ch in enumerate(text):
        code = ord(ch)
        if code > 127:
            return False, f"Character at position {i} ({ch!r}) is not ASCII"
        if code < 0:
            return False, f"Invalid character at position {i}"
    
    return True, "OK"
