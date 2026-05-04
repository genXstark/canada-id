"""Tests for local document app support utilities."""
from pathlib import Path

from PIL import Image

from canada_id.ai_config import get_provider_statuses, provider_status_markdown
from canada_id.sample_store import PRSampleStore
from canada_id.start_local import ensure_local_env
from canada_id.templates import generate_passport, generate_pr_card
from canada_id.web import _apply_edit_plan, _local_plan_from_prompt


def test_provider_statuses_include_expected_keys(monkeypatch):
    """Provider status reflects configured and missing env vars safely."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-12345678")
    monkeypatch.delenv("VENICE_ADMIN_KEY", raising=False)

    statuses = {item.env_var: item for item in get_provider_statuses()}

    assert statuses["OPENROUTER_API_KEY"].configured is True
    assert statuses["OPENROUTER_API_KEY"].preview.startswith("sk-t")
    assert statuses["VENICE_ADMIN_KEY"].configured is False
    assert "OPENROUTER_API_KEY" in provider_status_markdown()


def test_pr_sample_store_roundtrip(tmp_path: Path):
    """PR sample presets are persisted and loaded by name."""
    store = PRSampleStore(tmp_path / "samples.json")
    payload = {
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "pr_number": "123456789",
    }

    store.save("default_pr", payload)

    assert store.list_names() == ["default_pr"]
    assert store.load("default_pr") == payload


def test_generate_pr_card_uses_template_dimensions():
    """PR card generation uses the template's 300 DPI dimensions."""
    fields = {
        "document_type": "I",
        "country_code": "CAN",
        "document_number": "R12345678",
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "nationality": "CAN",
        "date_of_birth": "950523",
        "sex": "M",
        "expiry_date": "290523",
        "country_of_birth": "CANADA",
        "pr_number": "123456789",
        "optional_data_1": "PR1234567",
    }
    photo = Image.new("RGB", (400, 500), "gray")

    result = generate_pr_card(fields, photo=photo)

    assert result.image.size == (1011, 637)
    assert result.mrz_string


def test_generate_passport_uses_template_dimensions():
    """Passport generation uses the template's physical dimensions."""
    fields = {
        "document_type": "P",
        "country_code": "CAN",
        "document_number": "AB1234567",
        "passport_no": "AB1234567",
        "surname": "SMITH",
        "given_names": "JOHN ALEXANDER",
        "nationality": "CAN",
        "date_of_birth": "950523",
        "sex": "M",
        "expiry_date": "320523",
        "date_of_issue": "220523",
        "place_of_birth": "TORONTO",
    }
    photo = Image.new("RGB", (400, 520), "gray")

    result = generate_passport(fields, photo=photo)

    assert result.image.size == (1476, 1039)
    assert result.mrz_string


def test_ensure_local_env_copies_example(tmp_path: Path):
    """Startup helper creates .env from .env.example when missing."""
    (tmp_path / ".env.example").write_text("OPENROUTER_API_KEY=\n", encoding="utf-8")

    env_path = ensure_local_env(tmp_path)

    assert env_path.exists()
    assert env_path.read_text(encoding="utf-8") == "OPENROUTER_API_KEY=\n"


def test_local_image_edit_plan_and_apply():
    """Local enhancement path generates sane plan values and image output."""
    plan = _local_plan_from_prompt("make it sharper, more vivid, and brighter")
    src = Image.new("RGB", (120, 80), "gray")

    edited = _apply_edit_plan(src, plan)

    assert edited.size == src.size
    assert 0.5 <= plan.brightness <= 2.0
    assert 0.5 <= plan.contrast <= 2.0
    assert 0.5 <= plan.color <= 2.0
    assert 0.5 <= plan.sharpness <= 2.0