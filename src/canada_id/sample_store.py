"""Reusable PR-card sample storage for the local app."""
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_SAMPLE_PATH = Path.home() / ".canada-id" / "pr_samples.json"


class PRSampleStore:
    """Persist named PR-card sample payloads for reuse."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_SAMPLE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_names(self) -> list[str]:
        """Return stored sample names."""
        return sorted(self._read().keys())

    def load(self, name: str) -> dict[str, str]:
        """Load a named sample payload."""
        data = self._read()
        return data.get(name, {}).copy()

    def save(self, name: str, fields: dict[str, str]) -> None:
        """Store or update a named sample payload."""
        data = self._read()
        data[name] = fields
        self._write(data)

    def delete(self, name: str) -> None:
        """Delete a named sample if it exists."""
        data = self._read()
        if name in data:
            del data[name]
            self._write(data)

    def _read(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict[str, dict[str, str]]) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8",
        )