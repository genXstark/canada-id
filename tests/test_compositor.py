"""Tests for card compositor."""

import pytest
from PIL import Image

from canada_id.card.compositor import composite_barcode_on_card
from canada_id.card.layout import BarcodeRegion


@pytest.fixture
def card_image():
    """Create a white test card image (856x540 pixels = 10x scale)."""
    return Image.new("RGB", (856, 540), color=(255, 255, 255))


@pytest.fixture
def barcode_image():
    """Create a test barcode image."""
    return Image.new("1", (400, 100), color=0)


@pytest.fixture
def default_region():
    """Standard barcode region (left strip)."""
    return BarcodeRegion(
        x_frac=0.02,
        y_frac=0.05,
        w_frac=0.37,
        h_frac=0.90,
        rotation_deg=-90.0,
    )


def test_composite_returns_image(card_image, barcode_image, default_region):
    """Compositing returns an image."""
    result = composite_barcode_on_card(
        card_image,
        barcode_image,
        default_region,
    )
    assert isinstance(result, Image.Image)


def test_composite_preserves_card_size(
    card_image,
    barcode_image,
    default_region,
):
    """Composite image has same dimensions as card."""
    result = composite_barcode_on_card(
        card_image,
        barcode_image,
        default_region,
    )
    assert result.size == card_image.size


def test_composite_modifies_image(
    card_image,
    barcode_image,
    default_region,
):
    """Composite image is different from blank card."""
    result = composite_barcode_on_card(
        card_image,
        barcode_image,
        default_region,
    )
    card_bytes = card_image.tobytes()
    result_bytes = result.tobytes()
    assert card_bytes != result_bytes


def test_barcode_region_dataclass():
    """BarcodeRegion stores fractional coordinates."""
    region = BarcodeRegion(
        x_frac=0.1,
        y_frac=0.2,
        w_frac=0.3,
        h_frac=0.4,
        rotation_deg=0.0,
    )
    assert region.x_frac == 0.1
    assert region.rotation_deg == 0.0


def test_composite_no_rotation(card_image, barcode_image):
    """Compositing without rotation works."""
    region = BarcodeRegion(
        x_frac=0.1,
        y_frac=0.1,
        w_frac=0.8,
        h_frac=0.8,
        rotation_deg=0.0,
    )
    result = composite_barcode_on_card(
        card_image,
        barcode_image,
        region,
    )
    assert result.size == card_image.size


def test_composite_with_code39(card_image, barcode_image, default_region):
    """Compositing with Code 39 barcode works."""
    code39_img = Image.new("1", (300, 50), color=0)
    result = composite_barcode_on_card(
        card_image,
        barcode_image,
        default_region,
        code39_image=code39_img,
    )
    assert result.size == card_image.size
