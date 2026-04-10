"""ICAO 9303 MRZ check digit calculation."""

WEIGHTS = [7, 3, 1]

CHAR_VALUES = {}
for _i in range(10):
    CHAR_VALUES[str(_i)] = _i
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    CHAR_VALUES[_c] = _i + 10
CHAR_VALUES["<"] = 0


def compute_check_digit(field: str) -> str:
    """Compute ICAO 9303 weighted modulo-10 check digit.

    Args:
        field: MRZ field string (uppercase letters, digits, '<').

    Returns:
        Single digit character (0-9).

    Raises:
        ValueError: If field contains invalid characters.
    """
    total = 0
    for i, char in enumerate(field):
        if char not in CHAR_VALUES:
            raise ValueError(
                f"Invalid MRZ character at position {i}: {char!r}"
            )
        total += CHAR_VALUES[char] * WEIGHTS[i % 3]
    return str(total % 10)


def verify_check_digit(field: str, expected: str) -> bool:
    """Verify a check digit against a field value.

    Args:
        field: MRZ field string.
        expected: Expected check digit character.

    Returns:
        True if the check digit matches.
    """
    return compute_check_digit(field) == expected
