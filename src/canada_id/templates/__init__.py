"""Document template system package."""
from canada_id.templates.document_templates import (
    BarcodeSpec,
    DocumentTemplate,
    DocumentType,
    HologramSpec,
    MicrotextSpec,
    MrzSpec,
    PhotoSpec,
    TEMPLATES,
    TextFieldSpec,
    get_template,
    list_templates,
    template_choices,
)
from canada_id.templates.generator import (
    GeneratedDocument,
    generate_document,
    generate_drivers_license,
    generate_health_card,
    generate_passport,
    generate_pr_card,
)

__all__ = [
    "BarcodeSpec",
    "DocumentTemplate",
    "DocumentType",
    "GeneratedDocument",
    "HologramSpec",
    "MicrotextSpec",
    "MrzSpec",
    "PhotoSpec",
    "TEMPLATES",
    "TextFieldSpec",
    "generate_document",
    "generate_drivers_license",
    "generate_health_card",
    "generate_passport",
    "generate_pr_card",
    "get_template",
    "list_templates",
    "template_choices",
]
