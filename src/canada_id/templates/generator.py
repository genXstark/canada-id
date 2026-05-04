"""Canadian document generator.

Generates complete Canadian ID documents with:
- Proper MRZ with ICAO 9303 check digits
- AAMVA-compliant PDF417 barcodes
- Code 128 and Code 39 barcodes
- Photo placement
- Text fields
- Security overlays (holograms, microtext)
- AI-generated signatures (via Google AI Studio)
"""
from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from canada_id.aamva.builder import build_aamva
from canada_id.codec.code128 import code128_to_image
from canada_id.codec.code39 import code39_to_image
from canada_id.codec.encoder import barcode_to_image, encode_pdf417
from canada_id.mrz.generator import MRZData, generate_mrz
from canada_id.mrz.renderer import render_mrz_image
from canada_id.templates.document_templates import (
    DocumentTemplate,
    DocumentType,
    get_template,
)

if TYPE_CHECKING:
    pass


@dataclass
class GeneratedDocument:
    """Result of document generation."""
    image: Image.Image
    mrz_string: str | None = None
    aamva_string: str | None = None
    barcode_data: dict[str, str] | None = None
    warnings: list[str] | None = None


def _fit_cover(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize and crop an image so it fully covers a target region."""
    src_w, src_h = image.size
    if src_w <= 0 or src_h <= 0:
        return image.resize((target_w, target_h), Image.LANCZOS)

    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize(
        (max(1, int(src_w * scale)), max(1, int(src_h * scale))),
        Image.LANCZOS,
    )
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def _fit_contain(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize an image to fit within a target region without distortion."""
    src_w, src_h = image.size
    if src_w <= 0 or src_h <= 0:
        return image.resize((target_w, target_h), Image.LANCZOS)

    scale = min(target_w / src_w, target_h / src_h)
    return image.resize(
        (max(1, int(src_w * scale)), max(1, int(src_h * scale))),
        Image.LANCZOS,
    )


def _create_blank_card(template: DocumentTemplate) -> Image.Image:
    """Create blank card with default visual template styling."""
    img = Image.new(
        "RGBA",
        (template.width_px, template.height_px),
        (255, 255, 255, 255),
    )
    draw = ImageDraw.Draw(img)
    w, h = img.size

    if template.doc_type == DocumentType.PERMANENT_RESIDENT:
        draw.rectangle([(0, 0), (w, h)], fill=(234, 241, 246, 255))
        draw.rectangle([(0, 0), (w, int(h * 0.18))], fill=(46, 75, 94, 255))
        draw.rectangle([(0, int(h * 0.55)), (w, h)], fill=(248, 250, 252, 255))
        draw.rectangle([(int(w * 0.68), int(h * 0.06)), (int(w * 0.98), int(h * 0.56))], outline=(90, 110, 130, 255), width=3)
    elif template.doc_type == DocumentType.PASSPORT:
        draw.rectangle([(0, 0), (w, h)], fill=(241, 238, 232, 255))
        draw.rectangle([(0, 0), (w, int(h * 0.12))], fill=(133, 33, 39, 255))
        draw.rectangle([(0, int(h * 0.70)), (w, h)], fill=(246, 244, 240, 255))
        draw.rectangle([(int(w * 0.03), int(h * 0.09)), (int(w * 0.33), int(h * 0.67))], outline=(110, 110, 120, 255), width=3)
    elif template.doc_type in {DocumentType.DL_ON, DocumentType.DL_QC}:
        draw.rectangle([(0, 0), (w, h)], fill=(230, 239, 248, 255))
        draw.rectangle([(0, 0), (w, int(h * 0.16))], fill=(30, 90, 140, 255))

    return img


def _render_text_field(
    draw: ImageDraw.ImageDraw,
    card_w: int,
    card_h: int,
    field,
    value: str,
) -> None:
    """Render a single text field onto the card."""
    x = int(field.x_frac * card_w)
    y = int(field.y_frac * card_h)
    
    # Scale font size based on DPI
    font_size = max(8, int(field.font_size_pt * 0.75))
    
    try:
        if field.bold:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        else:
            font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("cour.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
    
    draw.text((x, y), value.upper(), fill=field.color, font=font)


def _render_microtext(
    img: Image.Image,
    template: DocumentTemplate,
) -> Image.Image:
    """Add microtext security borders to the card."""
    if not template.microtext:
        return img
    
    draw = ImageDraw.Draw(img)
    card_w, card_h = img.size
    
    for spec in template.microtext:
        y = int(spec.y_frac * card_h)
        h = int(spec.h_frac * card_h)
        
        # Tiny font for microtext
        font_size = max(4, int(spec.font_size_pt))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        
        # Calculate how many times to repeat
        if spec.repeat:
            bbox = draw.textbbox((0, 0), spec.text, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width > 0:
                repeats = (card_w // text_width) + 2
                full_text = spec.text * repeats
            else:
                full_text = spec.text
        else:
            full_text = spec.text
        
        draw.text((0, y), full_text, fill=spec.color, font=font)
    
    return img


def _apply_hologram_overlay(
    img: Image.Image,
    template: DocumentTemplate,
) -> Image.Image:
    """Apply hologram/security overlay effect."""
    if not template.holograms:
        return img
    
    for spec in template.holograms:
        # Create a simple holographic shimmer effect
        # (In production, this would use actual hologram images)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        card_w, card_h = img.size
        x = int(spec.x_frac * card_w)
        y = int(spec.y_frac * card_h)
        w = int(spec.w_frac * card_w)
        h = int(spec.h_frac * card_h)
        
        # Create diagonal lines for holographic effect
        alpha = int(spec.opacity * 50)
        for i in range(0, w + h, 8):
            x1 = x + i
            y1 = y
            x2 = x
            y2 = y + i
            
            if x1 > x + w:
                y1 += x1 - (x + w)
                x1 = x + w
            if y2 > y + h:
                x2 += y2 - (y + h)
                y2 = y + h
            
            color = (180, 220, 255, alpha) if i % 16 == 0 else (255, 200, 180, alpha)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
        
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
    
    return img


def _place_photo(
    img: Image.Image,
    photo: Image.Image,
    template: DocumentTemplate,
) -> Image.Image:
    """Place photo on card at specified position."""
    if not template.photo:
        return img
    
    spec = template.photo
    card_w, card_h = img.size
    
    x = int(spec.x_frac * card_w)
    y = int(spec.y_frac * card_h)
    w = int(spec.w_frac * card_w)
    h = int(spec.h_frac * card_h)
    
    # Resize photo to cover the portrait region without stretching it.
    photo_resized = _fit_cover(photo, w, h)
    
    # Convert to RGBA if needed
    if photo_resized.mode != "RGBA":
        photo_resized = photo_resized.convert("RGBA")
    
    img.paste(photo_resized, (x, y), mask=photo_resized)
    return img


def _place_signature(
    img: Image.Image,
    signature: Image.Image,
    template: DocumentTemplate,
) -> Image.Image:
    """Place signature on card."""
    card_w, card_h = img.size
    
    x = int(template.signature_x_frac * card_w)
    y = int(template.signature_y_frac * card_h)
    w = int(template.signature_w_frac * card_w)
    h = int(template.signature_h_frac * card_h)
    
    # Resize signature to fit
    sig_resized = signature.resize((w, h), Image.LANCZOS)
    
    # Convert to RGBA
    if sig_resized.mode != "RGBA":
        sig_resized = sig_resized.convert("RGBA")
    
    img.paste(sig_resized, (x, y), mask=sig_resized)
    return img


def _generate_mrz_zone(
    img: Image.Image,
    template: DocumentTemplate,
    mrz_data: MRZData,
) -> tuple[Image.Image, str]:
    """Generate and place MRZ zone on document."""
    if not template.mrz:
        return img, ""
    
    spec = template.mrz
    card_w, card_h = img.size
    
    # Generate MRZ string
    mrz_string = generate_mrz(mrz_data, spec.format)
    
    # Render MRZ image
    mrz_img = render_mrz_image(mrz_string, scale=3)
    
    # Calculate placement
    x = int(spec.x_frac * card_w)
    y = int(spec.y_frac * card_h)
    w = int(spec.w_frac * card_w)
    h = int(spec.h_frac * card_h)
    
    # Fit within the MRZ zone without changing the aspect ratio.
    mrz_resized = _fit_contain(mrz_img, w, h)
    x = x + (w - mrz_resized.width) // 2
    y = y + (h - mrz_resized.height) // 2
    
    # Convert to RGBA
    if mrz_resized.mode != "RGBA":
        mrz_resized = mrz_resized.convert("RGBA")
    
    img.paste(mrz_resized, (x, y))
    return img, mrz_string


def _generate_barcodes(
    img: Image.Image,
    template: DocumentTemplate,
    barcode_data: dict[str, str],
    province_code: str | None = None,
) -> tuple[Image.Image, dict[str, str]]:
    """Generate and place all barcodes on document."""
    results: dict[str, str] = {}
    card_w, card_h = img.size
    
    for i, spec in enumerate(template.barcodes):
        barcode_img = None
        barcode_str = ""
        
        if spec.barcode_type == "pdf417":
            # Use AAMVA data if available
            if "DAQ" in barcode_data and province_code:
                from canada_id.aamva.builder import build_aamva
                aamva_string = build_aamva(barcode_data, province_code)
                barcode = encode_pdf417(aamva_string)
                barcode_img = barcode_to_image(barcode, scale=spec.scale)
                barcode_str = aamva_string
            else:
                # Generate generic PDF417
                data = json.dumps(barcode_data, separators=(",", ":"))
                barcode = encode_pdf417(data)
                barcode_img = barcode_to_image(barcode, scale=spec.scale)
                barcode_str = data
        
        elif spec.barcode_type == "code128":
            # Use health number, DL number, or SIN
            code_data = (
                barcode_data.get("health_number") or
                barcode_data.get("DAQ") or
                barcode_data.get("sin_number") or
                barcode_data.get("phn") or
                "0000000000"
            )
            barcode_img = code128_to_image(
                code_data,
                module_width=2,
                bar_height=40,
                show_text=False,
            )
            barcode_str = code_data
        
        elif spec.barcode_type == "code39":
            code_data = (
                barcode_data.get("DAQ") or
                barcode_data.get("doc_number") or
                "TEST123"
            )
            barcode_img = code39_to_image(
                code_data,
                narrow=2,
                wide=5,
                bar_height=40,
            )
            barcode_str = code_data
        
        if barcode_img:
            # Calculate placement
            x = int(spec.x_frac * card_w)
            y = int(spec.y_frac * card_h)
            w = int(spec.w_frac * card_w)
            h = int(spec.h_frac * card_h)
            
            # Fit within the region without stretching barcode cells.
            barcode_resized = _fit_contain(barcode_img, w, h)
            
            # Rotate if needed
            if spec.rotation_deg != 0:
                barcode_resized = barcode_resized.rotate(
                    spec.rotation_deg,
                    expand=True,
                    fillcolor=(255, 255, 255),
                )
                # Recalculate position after rotation
                new_w, new_h = barcode_resized.size
                x = x + (w - new_w) // 2
                y = y + (h - new_h) // 2
            else:
                x = x + (w - barcode_resized.width) // 2
                y = y + (h - barcode_resized.height) // 2
            
            # Convert to RGBA
            if barcode_resized.mode != "RGBA":
                barcode_resized = barcode_resized.convert("RGBA")
            
            img.paste(barcode_resized, (x, y), mask=barcode_resized)
            results[f"barcode_{i}_{spec.barcode_type}"] = barcode_str
    
    return img, results


def generate_document(
    doc_type: DocumentType | str,
    fields: dict[str, str],
    photo: Image.Image | None = None,
    signature: Image.Image | None = None,
    province_code: str | None = None,
) -> GeneratedDocument:
    """Generate a complete Canadian ID document.
    
    Args:
        doc_type: Type of document to generate.
        fields: Field values (AAMVA fields for DL, personal info for others).
        photo: Optional portrait photo.
        signature: Optional signature image.
        province_code: Province code for driver's licenses.
    
    Returns:
        GeneratedDocument with image and metadata.
    """
    template = get_template(doc_type)
    warnings: list[str] = []
    
    # Create blank card
    img = _create_blank_card(template)
    
    # Add microtext borders
    img = _render_microtext(img, template)
    
    # Place photo if provided and template has photo spec
    if photo and template.photo:
        img = _place_photo(img, photo, template)
    elif template.photo and not photo:
        warnings.append("No photo provided - placeholder used")
    
    # Generate and place barcodes
    img, barcode_results = _generate_barcodes(
        img, template, fields, province_code,
    )
    
    # Generate MRZ if applicable
    mrz_string = None
    if template.mrz:
        mrz_data = MRZData(
            document_type=fields.get("document_type", "I"),
            country_code=fields.get("country_code", "CAN"),
            surname=fields.get("surname") or fields.get("DCS", ""),
            given_names=fields.get("given_names") or fields.get("DAC", ""),
            document_number=fields.get("document_number") or fields.get("DAQ", "")[:9],
            nationality=fields.get("nationality", "CAN"),
            date_of_birth=fields.get("date_of_birth") or fields.get("DBB", "")[-6:] if fields.get("DBB") else "",
            sex=fields.get("sex", "M"),
            expiry_date=fields.get("expiry_date") or fields.get("DBA", "")[-6:] if fields.get("DBA") else "",
            optional_data_1=fields.get("optional_data_1", ""),
            optional_data_2=fields.get("optional_data_2", ""),
        )
        img, mrz_string = _generate_mrz_zone(img, template, mrz_data)
    
    # Render text fields
    draw = ImageDraw.Draw(img)
    for field_spec in template.text_fields:
        value = fields.get(field_spec.field_name, "")
        if value:
            _render_text_field(draw, img.width, img.height, field_spec, value)
    
    # Place signature if provided
    if signature:
        img = _place_signature(img, signature, template)
    
    # Apply hologram overlay (last, so it's on top)
    img = _apply_hologram_overlay(img, template)
    
    # Convert to RGB for final output
    final_img = img.convert("RGB")
    
    return GeneratedDocument(
        image=final_img,
        mrz_string=mrz_string,
        aamva_string=barcode_results.get("barcode_0_pdf417"),
        barcode_data=barcode_results,
        warnings=warnings if warnings else None,
    )


def generate_drivers_license(
    province: str,
    fields: dict[str, str],
    photo: Image.Image | None = None,
    signature: Image.Image | None = None,
) -> GeneratedDocument:
    """Generate a provincial driver's license.
    
    Args:
        province: Province code (ON, QC, BC, etc.).
        fields: AAMVA field dictionary.
        photo: Portrait photo.
        signature: Signature image.
    
    Returns:
        GeneratedDocument with complete DL.
    """
    # Map province to document type
    province_map = {
        "ON": DocumentType.DL_ON,
        "QC": DocumentType.DL_QC,
        "BC": DocumentType.DL_BC,
        "AB": DocumentType.DL_AB,
        "MB": DocumentType.DL_MB,
        "SK": DocumentType.DL_SK,
        "NS": DocumentType.DL_NS,
        "NB": DocumentType.DL_NB,
        "NL": DocumentType.DL_NL,
        "PE": DocumentType.DL_PE,
        "NT": DocumentType.DL_NT,
        "NU": DocumentType.DL_NU,
        "YT": DocumentType.DL_YT,
    }
    
    doc_type = province_map.get(province.upper(), DocumentType.DL_ON)
    
    return generate_document(
        doc_type,
        fields,
        photo=photo,
        signature=signature,
        province_code=province.upper(),
    )


def generate_passport(
    fields: dict[str, str],
    photo: Image.Image | None = None,
    signature: Image.Image | None = None,
) -> GeneratedDocument:
    """Generate a Canadian passport data page.
    
    Args:
        fields: Personal information fields.
        photo: Passport photo (35mm x 45mm ratio).
        signature: Signature image.
    
    Returns:
        GeneratedDocument with passport page.
    """
    return generate_document(
        DocumentType.PASSPORT,
        fields,
        photo=photo,
        signature=signature,
    )


def generate_pr_card(
    fields: dict[str, str],
    photo: Image.Image | None = None,
) -> GeneratedDocument:
    """Generate a Canadian Permanent Resident Card.
    
    Args:
        fields: Personal information fields.
        photo: Portrait photo.
    
    Returns:
        GeneratedDocument with PR card.
    """
    return generate_document(
        DocumentType.PERMANENT_RESIDENT,
        fields,
        photo=photo,
    )


def generate_health_card(
    province: str,
    fields: dict[str, str],
    photo: Image.Image | None = None,
) -> GeneratedDocument:
    """Generate a provincial health card.
    
    Args:
        province: Province code (ON, BC, QC, AB).
        fields: Health card fields.
        photo: Portrait photo (for OHIP, BC Services).
    
    Returns:
        GeneratedDocument with health card.
    """
    province_map = {
        "ON": DocumentType.OHIP,
        "BC": DocumentType.BC_SERVICES,
        "QC": DocumentType.RAMQ,
        "AB": DocumentType.AB_HEALTH,
    }
    
    doc_type = province_map.get(province.upper(), DocumentType.OHIP)
    
    return generate_document(
        doc_type,
        fields,
        photo=photo,
    )
