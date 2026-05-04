"""Local startup helper for desktop mode."""
from __future__ import annotations

import shutil
from pathlib import Path


def ensure_local_env(project_root: Path) -> Path:
    """Ensure a local .env file exists, using .env.example when available."""
    env_path = project_root / ".env"
    if env_path.exists():
        return env_path

    example_path = project_root / ".env.example"
    if example_path.exists():
        shutil.copyfile(example_path, env_path)
    else:
        env_path.write_text("", encoding="utf-8")
    return env_path


def main() -> None:
    """Create local env file (if needed) and launch desktop app."""
    project_root = Path.cwd()
    ensure_local_env(project_root)

    from desktop import main as desktop_main

    desktop_main()


if __name__ == "__main__":
    main()