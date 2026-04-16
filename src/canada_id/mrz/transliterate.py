"""ICAO 9303 transliteration for MRZ fields.

Converts accented/special characters to MRZ-safe ASCII.
Based on ICAO Doc 9303 Part 3, Appendix 1 (Latin-based).
"""
from __future__ import annotations

# ICAO 9303 standard Latin-based transliteration map
LATIN_MAP: dict[str, str] = {
    "À": "A", "Á": "A", "Â": "A", "Ã": "A", "Ä": "AE",
    "Å": "AA", "Ā": "A", "Ă": "A", "Ą": "A",
    "Æ": "AE",
    "Ç": "C", "Ć": "C", "Ĉ": "C", "Č": "C", "Ċ": "C",
    "Ð": "D", "Ď": "D", "Đ": "D",
    "È": "E", "É": "E", "Ê": "E", "Ë": "E",
    "Ē": "E", "Ĕ": "E", "Ė": "E", "Ę": "E", "Ě": "E",
    "Ĝ": "G", "Ğ": "G", "Ġ": "G", "Ģ": "G",
    "Ĥ": "H", "Ħ": "H",
    "Ì": "I", "Í": "I", "Î": "I", "Ï": "I",
    "Ĩ": "I", "Ī": "I", "Ĭ": "I", "Į": "I", "İ": "I",
    "Ĳ": "IJ",
    "Ĵ": "J",
    "Ķ": "K",
    "Ĺ": "L", "Ļ": "L", "Ľ": "L", "Ŀ": "L", "Ł": "L",
    "Ñ": "N", "Ń": "N", "Ņ": "N", "Ň": "N", "Ŋ": "N",
    "Ò": "O", "Ó": "O", "Ô": "O", "Õ": "O", "Ö": "OE",
    "Ō": "O", "Ŏ": "O", "Ő": "O",
    "Ø": "OE",
    "Œ": "OE",
    "Ŕ": "R", "Ŗ": "R", "Ř": "R",
    "Ś": "S", "Ŝ": "S", "Ş": "S", "Š": "S", "Ș": "S",
    "Ţ": "T", "Ť": "T", "Ŧ": "T", "Ț": "T",
    "Þ": "TH",
    "Ù": "U", "Ú": "U", "Û": "U", "Ü": "UE",
    "Ũ": "U", "Ū": "U", "Ŭ": "U", "Ů": "U", "Ű": "U",
    "Ų": "U",
    "Ŵ": "W",
    "Ý": "Y", "Ŷ": "Y", "Ÿ": "Y",
    "Ź": "Z", "Ż": "Z", "Ž": "Z",
    "ß": "SS",
}

# Build lowercase map automatically
_FULL_MAP: dict[str, str] = {}
for _k, _v in LATIN_MAP.items():
    _FULL_MAP[_k] = _v
    _FULL_MAP[_k.lower()] = _v


def transliterate(text: str) -> str:
    """Transliterate text to MRZ-safe ASCII.

    Converts accented characters per ICAO 9303 rules.
    Preserves spaces (caller converts to < for MRZ).
    Strips any remaining non-ASCII after transliteration.

    Args:
        text: Input text, may contain accented characters.

    Returns:
        Uppercase ASCII string safe for MRZ encoding.
    """
    result = []
    for char in text:
        if char in _FULL_MAP:
            result.append(_FULL_MAP[char])
        elif char.isascii() and (char.isalpha() or char.isdigit()
                                 or char in " -<"):
            result.append(char.upper())
        elif char == " ":
            result.append(" ")
        # Drop any other character silently
    return "".join(result)


def transliterate_name(name: str) -> str:
    """Transliterate a name field for MRZ.

    Converts hyphens to spaces (MRZ standard), then
    transliterates all characters.

    Args:
        name: Name string (may contain accents, hyphens).

    Returns:
        MRZ-safe uppercase name.
    """
    name = name.replace("-", " ")
    return transliterate(name)
