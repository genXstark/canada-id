"""Environment-based AI provider configuration for local use.

This module intentionally reads secrets from the environment only.
It does not embed API keys in source files or persistent project storage.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _mask_secret(value: str | None) -> str:
    """Return a non-sensitive preview of a configured secret."""
    if not value:
        return "missing"
    if len(value) <= 8:
        return "configured"
    return f"{value[:4]}...{value[-4:]}"


@dataclass(frozen=True)
class ProviderStatus:
    """High-level status for a configured provider."""

    name: str
    configured: bool
    env_var: str
    preview: str


def get_provider_statuses() -> list[ProviderStatus]:
    """List supported providers and whether their keys are configured."""
    providers = [
        ("OpenRouter", "OPENROUTER_API_KEY"),
        ("Venice Admin", "VENICE_ADMIN_KEY"),
        ("Venice Inference", "VENICE_INFERENCE_KEY"),
        ("DeepSeek", "DEEPSEEK_API_KEY"),
        ("Gemini", "GEMINI_API_KEY"),
        ("Gemini General", "GEMINI_GENERAL_API_KEY"),
        ("Gemini Cipher Ops", "GEMINI_CIPHER_OPS_API_KEY"),
        ("Google AI", "GOOGLE_AI_API_KEY"),
        ("Google AI Studio", "GOOGLE_AI_STUDIO_API_KEY"),
        ("IProyal", "IPROYAL_API_KEY"),
    ]
    statuses: list[ProviderStatus] = []
    for name, env_var in providers:
        value = os.getenv(env_var)
        statuses.append(
            ProviderStatus(
                name=name,
                configured=bool(value),
                env_var=env_var,
                preview=_mask_secret(value),
            )
        )
    return statuses


def provider_status_markdown() -> str:
    """Render a compact, non-sensitive provider summary for the UI."""
    lines = ["Configured providers are read from environment variables:", ""]
    for item in get_provider_statuses():
        state = "configured" if item.configured else "missing"
        lines.append(
            f"- {item.name}: {state} via {item.env_var} ({item.preview})"
        )
    lines.append("")
    lines.append("Set values in your shell or a local .env file before launch.")
    return "\n".join(lines)