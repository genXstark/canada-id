"""Card layout definitions for barcode placement."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BarcodeRegion:
    """Fractional-coordinate region for barcode placement on a card.

    All coordinates are fractions of the card image dimensions
    (0.0 to 1.0), making layouts resolution-independent.

    Attributes:
        x_frac: Left edge as fraction of card width.
        y_frac: Top edge as fraction of card height.
        w_frac: Width as fraction of card width.
        h_frac: Height as fraction of card height.
        rotation_deg: Rotation angle in degrees (CCW positive).
    """

    x_frac: float
    y_frac: float
    w_frac: float
    h_frac: float
    rotation_deg: float


# Common Canadian province layouts
ONTARIO_BACK = BarcodeRegion(
    x_frac=0.0,
    y_frac=0.02,
    w_frac=0.37,
    h_frac=0.75,
    rotation_deg=0.0,
)
