"""Code 39 barcode encoder."""

from PIL import Image, ImageDraw, ImageFont

CODE39_TABLE: dict[str, str] = {
    "0": "000110100",
    "1": "100100001",
    "2": "001100001",
    "3": "101100000",
    "4": "000110001",
    "5": "100110000",
    "6": "001110000",
    "7": "000100101",
    "8": "100100100",
    "9": "001100100",
    "A": "100001001",
    "B": "001001001",
    "C": "101001000",
    "D": "000011001",
    "E": "100011000",
    "F": "001011000",
    "G": "000001101",
    "H": "100001100",
    "I": "001001100",
    "J": "000011100",
    "K": "100000011",
    "L": "001000011",
    "M": "101000010",
    "N": "000010011",
    "O": "100010010",
    "P": "001010010",
    "Q": "000000111",
    "R": "100000110",
    "S": "001000110",
    "T": "000010110",
    "U": "110000001",
    "V": "011000001",
    "W": "111000000",
    "X": "010010001",
    "Y": "110010000",
    "Z": "011010000",
    "-": "010000101",
    ".": "110000100",
    " ": "011000100",
    "$": "010101000",
    "/": "010100010",
    "+": "010001010",
    "%": "000101010",
    "*": "010010100",
}


def _validate_text(text: str) -> str:
    """Validate and wrap text with start/stop characters.

    Args:
        text: Input text to encode.

    Returns:
        Uppercased text wrapped with '*' start/stop chars.

    Raises:
        ValueError: If text contains characters not in Code 39.
    """
    text = text.upper().strip()
    chars = list("*" + text + "*")
    for ch in chars:
        if ch not in CODE39_TABLE:
            raise ValueError(f"Character {ch!r} not in Code 39 alphabet")
    return text


def _compute_bar_widths(pattern: str, narrow: int, wide: int) -> list[int]:
    """Convert a 9-bit pattern string to bar widths.

    Args:
        pattern: 9-char string of '0' (narrow) / '1' (wide).
        narrow: Narrow bar width in pixels.
        wide: Wide bar width in pixels.

    Returns:
        List of 9 integer widths.
    """
    return [wide if b == "1" else narrow for b in pattern]


def encode_code39(text: str) -> list[list[int]]:
    """Encode text as Code 39 barcode.

    Args:
        text: Text to encode (A-Z, 0-9, -.$/+% and space).

    Returns:
        2D bit array (list of rows, each row is list of 0/1).

    Raises:
        ValueError: If text contains invalid characters.
    """
    text = _validate_text(text)
    chars = list("*" + text + "*")
    narrow, wide = 1, 1

    row: list[int] = []
    for idx, ch in enumerate(chars):
        widths = _compute_bar_widths(CODE39_TABLE[ch], narrow, wide)
        for i, w in enumerate(widths):
            bit = 1 if i % 2 == 0 else 0
            row.extend([bit] * w)
        if idx < len(chars) - 1:
            row.extend([0] * narrow)

    return [row]


def code39_to_image(
    text: str,
    narrow: int = 2,
    wide: int = 5,
    bar_height: int = 50,
) -> Image.Image:
    """Generate Code 39 barcode as PIL Image.

    Args:
        text: Text to encode (A-Z, 0-9, -.$/+% and space).
        narrow: Narrow bar/space width in pixels.
        wide: Wide bar/space width in pixels.
        bar_height: Height of bars in pixels.

    Returns:
        PIL Image of the rendered barcode.

    Raises:
        ValueError: If text contains invalid characters.
    """
    text = _validate_text(text)
    chars = list("*" + text + "*")

    quiet_zone = narrow * 5
    inter_char_gap = narrow
    text_height = 16
    padding = 4

    total_width = quiet_zone * 2
    for idx, ch in enumerate(chars):
        widths = _compute_bar_widths(CODE39_TABLE[ch], narrow, wide)
        total_width += sum(widths)
        if idx < len(chars) - 1:
            total_width += inter_char_gap

    img_h = bar_height + text_height + padding
    img = Image.new("RGB", (total_width, img_h), "white")
    draw = ImageDraw.Draw(img)

    x = quiet_zone
    for idx, ch in enumerate(chars):
        widths = _compute_bar_widths(CODE39_TABLE[ch], narrow, wide)
        for i, w in enumerate(widths):
            if i % 2 == 0:
                draw.rectangle(
                    [x, 0, x + w - 1, bar_height - 1],
                    fill="black",
                )
            x += w
        if idx < len(chars) - 1:
            x += inter_char_gap

    label = "*" + text + "*"
    try:
        font = ImageFont.truetype("cour.ttf", 11)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    tx = (total_width - tw) // 2
    ty = bar_height + padding
    draw.text((tx, ty), label, fill="black", font=font)

    return img
