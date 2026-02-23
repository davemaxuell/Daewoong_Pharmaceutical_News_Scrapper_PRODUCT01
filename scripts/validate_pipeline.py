#!/usr/bin/env python
"""Lightweight validation checks for pipeline consistency."""

from __future__ import annotations

import json
import py_compile
from pathlib import Path


def check_compile(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for p in paths:
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            errors.append(f"Compile failed: {p} -> {e}")
    return errors


def check_keyword_team_consistency(project_root: Path) -> list[str]:
    errors: list[str] = []
    try:
        import sys

        sys.path.insert(0, str(project_root))
        from src.keywords import KEYWORDS  # type: ignore
        from src.team_definitions import TEAM_DEFINITIONS  # type: ignore
    except Exception as e:
        return [f"Import failed for keywords/team_definitions: {e}"]

    if not KEYWORDS:
        errors.append("KEYWORDS is empty")
    if not TEAM_DEFINITIONS:
        errors.append("TEAM_DEFINITIONS is empty")

    for team, info in TEAM_DEFINITIONS.items():
        if not info.get("keywords"):
            errors.append(f"Team has no keywords: {team}")
    return errors


def check_scraper_overrides(project_root: Path) -> list[str]:
    errors: list[str] = []
    override_path = project_root / "config" / "scraper_sources.json"
    if not override_path.exists():
        return errors

    try:
        overrides = json.loads(override_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"Invalid JSON in {override_path}: {e}"]

    if not isinstance(overrides, dict):
        return [f"{override_path} must be a JSON object"]

    import sys

    sys.path.insert(0, str(project_root))
    try:
        from src.multi_source_scraper import MultiSourceScraper  # type: ignore
    except Exception as e:
        return [f"Import failed for MultiSourceScraper: {e}"]

    known = set(MultiSourceScraper.SCRAPERS_CONFIG.keys())
    for key, cfg in overrides.items():
        if key not in known:
            errors.append(f"Unknown source key in overrides: {key}")
        if not isinstance(cfg, dict):
            errors.append(f"Override for {key} must be an object")
            continue
        for field in cfg.keys():
            if field not in {"enabled", "description", "args", "use_internal_days_back"}:
                errors.append(f"Unsupported override field for {key}: {field}")
    return errors


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]

    compile_targets = [
        project_root / "src" / "run_pipeline.py",
        project_root / "src" / "multi_source_scraper.py",
        project_root / "src" / "ai_summarizer_gemini.py",
        project_root / "src" / "email_sender.py",
        project_root / "src" / "keywords.py",
        project_root / "src" / "team_definitions.py",
    ]

    errors: list[str] = []
    errors.extend(check_compile(compile_targets))
    errors.extend(check_keyword_team_consistency(project_root))
    errors.extend(check_scraper_overrides(project_root))

    if errors:
        print("[FAIL] Pipeline validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1

    print("[OK] Pipeline validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

