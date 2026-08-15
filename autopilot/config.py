"""Loads profile.yaml — the single source of truth for the whole pipeline."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profile.yaml"
DB_PATH = ROOT / "data" / "autopilot.db"
DIGEST_DIR = ROOT / "docs" / "DAILY"


@lru_cache(maxsize=1)
def load_profile(path: Path | None = None) -> dict[str, Any]:
    """Read and cache profile.yaml."""
    target = path or PROFILE_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"profile.yaml not found at {target}. It holds every application "
            "answer and is required. It is gitignored, so a fresh clone starts "
            "without one: copy profile.example.yaml to profile.yaml and fill it in."
        )
    with target.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def flat_skills(profile: dict[str, Any]) -> set[str]:
    """Every skill tag across all categories, lowercased."""
    tags = profile.get("skills_tags", {})
    out: set[str] = set()
    for values in tags.values():
        for value in values:
            out.add(value.lower())
    return out
