"""Canadian document template system.

Provides templates for generating complete Canadian ID documents
with proper barcode placement, MRZ zones, and security features.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from PIL import Image


class DocumentType(Enum):
    """Supported Canadian document types."""
    # Federal documents
    PASSPORT = "passport"
    PERMANENT_RESIDENT = "pr_card"
    SIN_CARD = "sin_card"
    
    # Driver's licenses (by province)
    DL_ON = "dl_on"  # Ontario
    DL_QC = "dl_qc"  # Quebec
    DL_BC = "dl_bc"  # British Columbia
    DL_AB = "dl_ab"  # Alberta
    DL_MB = "dl_mb"  # Manitoba
    DL_SK = "dl_sk"  # Saskatchewan
    DL_NS = "dl_ns"  # Nova Scotia
    DL_NB = "dl_nb"  # New Brunswick
    DL_NL = "dl_nl"  # Newfoundland
    DL_PE = "dl_pe"  # Prince Edward Island
    DL_NT = "dl_nt"  # Northwest Territories
    DL_NU = "dl_nu"  # Nunavut
    DL_YT = "dl_yt"  # Yukon
    
    # Health cards
    OHIP = "ohip"              # Ontario Health Insurance Plan
    BC_SERVICES = "bc_services"  # BC Services Card
    RAMQ = "ramq"               # Quebec Health Card
    AB_HEALTH = "ab_health"     # Alberta Health Card
    
    # Other documents
    BIRTH_CERT_ON = "birth_cert_on"
    BIRTH_CERT_QC = "birth_cert_qc"
    BIRTH_CERT_BC = "birth_cert_bc"


@dataclass
class BarcodeSpec:
    """Barcode placement and type specification."""
    barcode_type: str  # "pdf417", "code128", "code39", "qr"
    x_frac: float      # X position as fraction of card width
    y_frac: float      # Y position as fraction of card height
    w_frac: float      # Width as fraction
    h_frac: float      # Height as fraction
    rotation_deg: float = 0.0
    scale: int = 3


@dataclass
class MrzSpec:
    """MRZ zone placement specification."""
    format: str        # "TD1", "TD2", "TD3"
    x_frac: float
    y_frac: float
    w_frac: float
    h_frac: float


@dataclass
class PhotoSpec:
    """Photo placement specification."""
    x_frac: float
    y_frac: float
    w_frac: float
    h_frac: float
    aspect_ratio: float = 1.25  # Height/width


@dataclass
class TextFieldSpec:
    """Text field placement specification."""
    field_name: str
    label: str
    x_frac: float
    y_frac: float
    w_frac: float
    font_size_pt: int = 10
    font_family: str = "Arial"
    bold: bool = False
    color: str = "#000000"


@dataclass
class HologramSpec:
    """Hologram overlay specification."""
    overlay_path: str | None = None
    x_frac: float = 0.0
    y_frac: float = 0.0
    w_frac: float = 1.0
    h_frac: float = 1.0
    opacity: float = 0.3


@dataclass
class MicrotextSpec:
    """Microtext security feature specification."""
    text: str
    font_size_pt: float = 3.0
    x_frac: float = 0.0
    y_frac: float = 0.0
    w_frac: float = 1.0
    h_frac: float = 0.02
    color: str = "#808080"
    repeat: bool = True


@dataclass
class DocumentTemplate:
    """Complete document template specification."""
    doc_type: DocumentType
    name: str
    description: str
    
    # Card dimensions (mm)
    width_mm: float = 85.6  # ID-1 standard
    height_mm: float = 53.98
    
    # Resolution for rendering
    dpi: int = 300
    
    # Component specifications
    photo: PhotoSpec | None = None
    mrz: MrzSpec | None = None
    barcodes: list[BarcodeSpec] = field(default_factory=list)
    text_fields: list[TextFieldSpec] = field(default_factory=list)
    holograms: list[HologramSpec] = field(default_factory=list)
    microtext: list[MicrotextSpec] = field(default_factory=list)
    
    # Background template path (if any)
    background_path: str | None = None
    
    # Signature specification
    signature_x_frac: float = 0.0
    signature_y_frac: float = 0.0
    signature_w_frac: float = 0.25
    signature_h_frac: float = 0.08
    
    @property
    def width_px(self) -> int:
        """Card width in pixels at configured DPI."""
        return int(self.width_mm * self.dpi / 25.4)
    
    @property
    def height_px(self) -> int:
        """Card height in pixels at configured DPI."""
        return int(self.height_mm * self.dpi / 25.4)


# ═══════════════════════════════════════════════════════════════
# TEMPLATE DEFINITIONS
# ═══════════════════════════════════════════════════════════════

TEMPLATES: dict[DocumentType, DocumentTemplate] = {}


def _reg(template: DocumentTemplate) -> None:
    """Register a document template."""
    TEMPLATES[template.doc_type] = template


# ─── ONTARIO DRIVER'S LICENSE ────────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.DL_ON,
    name="Ontario Driver's License",
    description="Ontario G-class driver's license (ID-1 format)",
    photo=PhotoSpec(
        x_frac=0.72, y_frac=0.15,
        w_frac=0.22, h_frac=0.45,
    ),
    barcodes=[
        BarcodeSpec(
            barcode_type="pdf417",
            x_frac=0.02, y_frac=0.05,
            w_frac=0.35, h_frac=0.90,
            rotation_deg=-90.0,
            scale=3,
        ),
    ],
    text_fields=[
        TextFieldSpec("DCS", "Family Name", 0.40, 0.12, 0.30, 11, bold=True),
        TextFieldSpec("DAC", "First Name", 0.40, 0.22, 0.30, 11),
        TextFieldSpec("DAD", "Middle Name", 0.40, 0.30, 0.30, 9),
        TextFieldSpec("DBB", "Date of Birth", 0.40, 0.40, 0.25, 9),
        TextFieldSpec("DAG", "Address", 0.40, 0.50, 0.50, 8),
        TextFieldSpec("DAQ", "License Number", 0.40, 0.70, 0.30, 10, bold=True),
        TextFieldSpec("DBA", "Expiry", 0.72, 0.65, 0.20, 9),
        TextFieldSpec("DCA", "Class", 0.72, 0.75, 0.10, 12, bold=True),
    ],
    holograms=[
        HologramSpec(opacity=0.25),
    ],
    microtext=[
        MicrotextSpec(
            text="ONTARIO DRIVER'S LICENCE ",
            y_frac=0.02, h_frac=0.02,
        ),
        MicrotextSpec(
            text="ONTARIO DRIVER'S LICENCE ",
            y_frac=0.96, h_frac=0.02,
        ),
    ],
    signature_x_frac=0.40,
    signature_y_frac=0.82,
    signature_w_frac=0.30,
    signature_h_frac=0.10,
))


# ─── QUEBEC DRIVER'S LICENSE ─────────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.DL_QC,
    name="Quebec Driver's License",
    description="Quebec permis de conduire (ID-1 format)",
    photo=PhotoSpec(
        x_frac=0.04, y_frac=0.18,
        w_frac=0.25, h_frac=0.50,
    ),
    barcodes=[
        BarcodeSpec(
            barcode_type="pdf417",
            x_frac=0.65, y_frac=0.05,
            w_frac=0.32, h_frac=0.90,
            rotation_deg=-90.0,
            scale=3,
        ),
    ],
    text_fields=[
        TextFieldSpec("DCS", "Nom / Name", 0.32, 0.12, 0.30, 11, bold=True),
        TextFieldSpec("DAC", "Prénom / First Name", 0.32, 0.24, 0.30, 10),
        TextFieldSpec("DBB", "Date naissance", 0.32, 0.36, 0.25, 9),
        TextFieldSpec("DAG", "Adresse", 0.32, 0.48, 0.30, 8),
        TextFieldSpec("DAQ", "No permis", 0.04, 0.75, 0.30, 10, bold=True),
        TextFieldSpec("DBA", "Expire", 0.32, 0.75, 0.20, 9),
        TextFieldSpec("DCA", "Classe", 0.04, 0.85, 0.10, 12, bold=True),
    ],
    holograms=[
        HologramSpec(opacity=0.20),
    ],
    microtext=[
        MicrotextSpec(
            text="SOCIÉTÉ DE L'ASSURANCE AUTOMOBILE DU QUÉBEC ",
            y_frac=0.02, h_frac=0.02,
        ),
    ],
    signature_x_frac=0.04,
    signature_y_frac=0.65,
    signature_w_frac=0.25,
    signature_h_frac=0.08,
))


# ─── CANADIAN PASSPORT ───────────────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.PASSPORT,
    name="Canadian Passport",
    description="Canadian passport data page (TD3 MRZ)",
    width_mm=125.0,  # Passport is larger
    height_mm=88.0,
    photo=PhotoSpec(
        x_frac=0.04, y_frac=0.10,
        w_frac=0.28, h_frac=0.55,
        aspect_ratio=1.33,
    ),
    mrz=MrzSpec(
        format="TD3",
        x_frac=0.02, y_frac=0.72,
        w_frac=0.96, h_frac=0.26,
    ),
    text_fields=[
        TextFieldSpec("surname", "Surname / Nom", 0.35, 0.12, 0.40, 12, bold=True),
        TextFieldSpec("given_names", "Given Names / Prénoms", 0.35, 0.24, 0.40, 11),
        TextFieldSpec("nationality", "Nationality / Nationalité", 0.35, 0.36, 0.20, 9),
        TextFieldSpec("date_of_birth", "Date of Birth", 0.35, 0.44, 0.20, 9),
        TextFieldSpec("sex", "Sex / Sexe", 0.60, 0.44, 0.10, 9),
        TextFieldSpec("place_of_birth", "Place of Birth", 0.35, 0.52, 0.30, 9),
        TextFieldSpec("date_of_issue", "Date of Issue", 0.70, 0.36, 0.20, 9),
        TextFieldSpec("passport_no", "Passport No.", 0.70, 0.12, 0.25, 11, bold=True),
        TextFieldSpec("expiry_date", "Date of Expiry", 0.70, 0.52, 0.20, 9),
    ],
    holograms=[
        HologramSpec(opacity=0.15),
    ],
    signature_x_frac=0.35,
    signature_y_frac=0.60,
    signature_w_frac=0.30,
    signature_h_frac=0.08,
))


# ─── PERMANENT RESIDENT CARD ─────────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.PERMANENT_RESIDENT,
    name="Permanent Resident Card",
    description="Canadian PR Card (TD1 MRZ)",
    photo=PhotoSpec(
        x_frac=0.72, y_frac=0.08,
        w_frac=0.24, h_frac=0.50,
    ),
    mrz=MrzSpec(
        format="TD1",
        x_frac=0.02, y_frac=0.62,
        w_frac=0.96, h_frac=0.36,
    ),
    text_fields=[
        TextFieldSpec("surname", "Family Name", 0.04, 0.08, 0.40, 10, bold=True),
        TextFieldSpec("given_names", "Given Names", 0.04, 0.18, 0.40, 10),
        TextFieldSpec("date_of_birth", "Date of Birth", 0.04, 0.30, 0.20, 9),
        TextFieldSpec("sex", "Sex", 0.30, 0.30, 0.10, 9),
        TextFieldSpec("country_of_birth", "Country of Birth", 0.04, 0.40, 0.30, 9),
        TextFieldSpec("pr_number", "PR Number", 0.04, 0.50, 0.35, 9),
    ],
    holograms=[
        HologramSpec(opacity=0.20),
    ],
))


# ─── ONTARIO HEALTH CARD (OHIP) ──────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.OHIP,
    name="Ontario Health Card",
    description="Ontario OHIP photo health card",
    photo=PhotoSpec(
        x_frac=0.04, y_frac=0.15,
        w_frac=0.22, h_frac=0.55,
    ),
    barcodes=[
        BarcodeSpec(
            barcode_type="code128",
            x_frac=0.30, y_frac=0.78,
            w_frac=0.65, h_frac=0.18,
            rotation_deg=0.0,
        ),
    ],
    text_fields=[
        TextFieldSpec("health_number", "Health Number", 0.30, 0.12, 0.35, 12, bold=True),
        TextFieldSpec("version_code", "Version", 0.68, 0.12, 0.10, 10),
        TextFieldSpec("surname", "Name", 0.30, 0.28, 0.50, 11),
        TextFieldSpec("date_of_birth", "Date of Birth", 0.30, 0.42, 0.25, 10),
        TextFieldSpec("sex", "Sex", 0.60, 0.42, 0.10, 10),
        TextFieldSpec("expiry_date", "Expiry", 0.30, 0.56, 0.25, 10),
    ],
    holograms=[
        HologramSpec(opacity=0.15),
    ],
    microtext=[
        MicrotextSpec(
            text="MINISTRY OF HEALTH ONTARIO ",
            y_frac=0.02, h_frac=0.015,
        ),
    ],
))


# ─── BC SERVICES CARD ────────────────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.BC_SERVICES,
    name="BC Services Card",
    description="British Columbia Services Card (combined driver's license + health)",
    photo=PhotoSpec(
        x_frac=0.72, y_frac=0.12,
        w_frac=0.24, h_frac=0.50,
    ),
    barcodes=[
        BarcodeSpec(
            barcode_type="pdf417",
            x_frac=0.02, y_frac=0.05,
            w_frac=0.30, h_frac=0.90,
            rotation_deg=-90.0,
        ),
        BarcodeSpec(
            barcode_type="code128",
            x_frac=0.35, y_frac=0.80,
            w_frac=0.35, h_frac=0.15,
        ),
    ],
    text_fields=[
        TextFieldSpec("surname", "Surname", 0.35, 0.10, 0.35, 11, bold=True),
        TextFieldSpec("given_names", "Given Names", 0.35, 0.22, 0.35, 10),
        TextFieldSpec("date_of_birth", "DOB", 0.35, 0.35, 0.20, 9),
        TextFieldSpec("phn", "PHN", 0.35, 0.48, 0.30, 10, bold=True),
        TextFieldSpec("dl_number", "DL Number", 0.35, 0.60, 0.30, 10),
    ],
    holograms=[
        HologramSpec(opacity=0.20),
    ],
))


# ─── SIN CARD ────────────────────────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.SIN_CARD,
    name="Social Insurance Number Card",
    description="Canadian SIN card",
    photo=None,  # SIN cards have no photo
    barcodes=[
        BarcodeSpec(
            barcode_type="code128",
            x_frac=0.15, y_frac=0.70,
            w_frac=0.70, h_frac=0.20,
        ),
    ],
    text_fields=[
        TextFieldSpec("sin_number", "Social Insurance Number", 0.10, 0.25, 0.80, 18, bold=True),
        TextFieldSpec("surname", "Name", 0.10, 0.45, 0.80, 12),
    ],
))


# ─── ONTARIO BIRTH CERTIFICATE ───────────────────────────────

_reg(DocumentTemplate(
    doc_type=DocumentType.BIRTH_CERT_ON,
    name="Ontario Birth Certificate",
    description="Ontario long-form birth certificate",
    width_mm=215.9,  # Letter size
    height_mm=279.4,
    barcodes=[
        BarcodeSpec(
            barcode_type="pdf417",
            x_frac=0.60, y_frac=0.85,
            w_frac=0.35, h_frac=0.10,
        ),
    ],
    text_fields=[
        TextFieldSpec("registration_number", "Registration Number", 0.60, 0.08, 0.35, 10),
        TextFieldSpec("child_surname", "Surname at Birth", 0.10, 0.20, 0.40, 14, bold=True),
        TextFieldSpec("child_given_names", "Given Names", 0.10, 0.26, 0.40, 14),
        TextFieldSpec("date_of_birth", "Date of Birth", 0.10, 0.34, 0.25, 12),
        TextFieldSpec("place_of_birth_city", "Place of Birth", 0.45, 0.34, 0.30, 12),
        TextFieldSpec("sex", "Sex", 0.10, 0.40, 0.10, 12),
        TextFieldSpec("mother_surname", "Mother's Surname at Birth", 0.10, 0.50, 0.35, 11),
        TextFieldSpec("mother_given_names", "Mother's Given Names", 0.10, 0.55, 0.35, 11),
        TextFieldSpec("father_surname", "Father's Surname", 0.55, 0.50, 0.35, 11),
        TextFieldSpec("father_given_names", "Father's Given Names", 0.55, 0.55, 0.35, 11),
        TextFieldSpec("date_registered", "Date Registered", 0.10, 0.65, 0.25, 10),
    ],
    holograms=[
        HologramSpec(opacity=0.10),
    ],
))


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_template(doc_type: DocumentType | str) -> DocumentTemplate:
    """Get a document template by type.
    
    Args:
        doc_type: DocumentType enum or string key.
        
    Returns:
        DocumentTemplate for the specified type.
        
    Raises:
        KeyError: If template not found.
    """
    if isinstance(doc_type, str):
        doc_type = DocumentType(doc_type)
    
    if doc_type not in TEMPLATES:
        raise KeyError(f"No template for document type: {doc_type}")
    
    return TEMPLATES[doc_type]


def list_templates() -> list[tuple[str, str]]:
    """List all available templates.
    
    Returns:
        List of (key, name) tuples.
    """
    return [
        (t.doc_type.value, t.name)
        for t in TEMPLATES.values()
    ]


def template_choices() -> list[str]:
    """Get template dropdown choices.
    
    Returns:
        List of "key - name" strings for UI dropdowns.
    """
    return [
        f"{t.doc_type.value} - {t.name}"
        for t in TEMPLATES.values()
    ]
