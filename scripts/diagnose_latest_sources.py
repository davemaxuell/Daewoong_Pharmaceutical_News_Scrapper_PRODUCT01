#!/usr/bin/env python
"""Inspect each enabled source and report the latest item seen per scraper."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.env_config import load_project_env

load_project_env()

from src.multi_source_scraper import MultiSourceScraper  # type: ignore


WIDE_LOOKBACK_DAYS: dict[str, Any] = {
    "fda_recalls": None,
    "fda_warning_letters": 30,
    "pmda": 365,
    "pics": 120,
    "ispe": 120,
    "gmp_journal": 60,
    "pharmaceutical_online": 60,
    "default": 30,
}

BLOCK_PROBE_URLS: dict[str, str] = {
    "pda": "https://www.pda.org/pda-letter-portal",
}
SOURCE_HEALTH_STALE_DAYS = max(1, int(os.getenv("SOURCE_HEALTH_STALE_DAYS", "7")))


def _probe_known_block(source_key: str) -> tuple[bool, str | None]:
    url = BLOCK_PROBE_URLS.get(source_key)
    if not url:
        return False, None

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        text = response.text.lower()
        if response.status_code == 403 or "cloudflare" in text or "access denied" in text:
            return True, f"blocked by upstream protection ({response.status_code})"
    except Exception as exc:
        return False, f"probe failed: {exc}"

    return False, None


def _classify_status(item: dict[str, Any]) -> tuple[str, str]:
    error_text = str(item.get("error") or "")
    lowered_error = error_text.lower()
    if error_text:
        if any(marker in lowered_error for marker in ["blocked", "cloudflare", "access denied", "denied"]):
            return "blocked", error_text
        return "error", error_text

    if item.get("recent_count", 0) > 0:
        return "healthy", "recent items found"

    if item.get("wide_count", 0) > 0:
        latest = item.get("wide_latest") or item.get("recent_latest")
        if latest:
            try:
                latest_dt = datetime.fromisoformat(str(latest))
                age_days = max(0, (datetime.now(latest_dt.tzinfo) - latest_dt).days) if latest_dt.tzinfo else max(
                    0, (datetime.now() - latest_dt).days
                )
                if age_days <= SOURCE_HEALTH_STALE_DAYS:
                    return "healthy", (
                        f"no items in the immediate window, but the latest item is only {age_days} days old "
                        f"(threshold {SOURCE_HEALTH_STALE_DAYS} days)"
                    )
                return "stale", (
                    f"no recent items in the configured window; latest item is {age_days} days old "
                    f"(threshold {SOURCE_HEALTH_STALE_DAYS} days)"
                )
            except Exception:
                pass
        return "stale", f"no recent items in the configured window (threshold {SOURCE_HEALTH_STALE_DAYS} days)"

    blocked, reason = _probe_known_block(item["source_key"])
    if blocked:
        return "blocked", reason or "blocked by upstream protection"

    return "unknown", "no recent or fallback items found"


def _fetch_with_fallback(source_key: str, config: dict[str, Any], days_back: int) -> dict[str, Any]:
    scraper = config["class"](**config.get("args", {}))

    def run_fetch(target_days: Any):
        kwargs: dict[str, Any] = {}
        if source_key == "pmda":
            kwargs = {"days_back": 365, "max_pdfs": 5}
        elif target_days is None:
            kwargs = {"days_back": None}
        else:
            kwargs = {"days_back": target_days}
        return scraper.fetch_news(**kwargs)

    recent_articles = run_fetch(days_back)
    recent_dated = [a for a in recent_articles if getattr(a, "published", None)]
    recent_latest = max((a.published for a in recent_dated), default=None)

    result = {
        "source_key": source_key,
        "description": config.get("description", source_key),
        "recent_count": len(recent_articles),
        "recent_latest": recent_latest.isoformat() if recent_latest else None,
        "recent_titles": [getattr(a, "title", "") for a in recent_articles[:3]],
    }

    if recent_articles:
        status, reason = _classify_status(result)
        result["status"] = status
        result["status_reason"] = reason
        return result

    wide_days = WIDE_LOOKBACK_DAYS.get(source_key, WIDE_LOOKBACK_DAYS["default"])
    wide_articles = run_fetch(wide_days)
    wide_dated = [a for a in wide_articles if getattr(a, "published", None)]
    wide_latest = max((a.published for a in wide_dated), default=None)

    result.update(
        {
            "wide_days": wide_days,
            "wide_count": len(wide_articles),
            "wide_latest": wide_latest.isoformat() if wide_latest else None,
            "wide_titles": [getattr(a, "title", "") for a in wide_articles[:3]],
        }
    )
    status, reason = _classify_status(result)
    result["status"] = status
    result["status_reason"] = reason
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose latest items per enabled source.")
    parser.add_argument("--days", type=int, default=2, help="Recent lookback window.")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    scraper = MultiSourceScraper()
    results = []

    for source_key, config in scraper.scrapers_config.items():
        if not config.get("enabled", True):
            continue
        print(f"[CHECK] {source_key}")
        try:
            results.append(_fetch_with_fallback(source_key, config, args.days))
        except Exception as exc:
            results.append(
                {
                    "source_key": source_key,
                    "description": config.get("description", source_key),
                    "error": str(exc),
                }
            )

    payload = {
        "generated_at": datetime.now().isoformat(),
        "recent_days": args.days,
        "stale_threshold_days": SOURCE_HEALTH_STALE_DAYS,
        "results": results,
    }

    output_path = args.output
    if not output_path:
        output_dir = PROJECT_ROOT / "data" / "diagnostics"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"latest_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    latest_path = PROJECT_ROOT / "data" / "diagnostics" / "latest_source_health.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("")
    print("Latest source summary")
    print("-" * 60)
    for item in results:
        if item.get("error"):
            print(f"{item['source_key']}: {item.get('status', 'error')} - {item['error']}")
            continue
        if item.get("recent_count", 0) > 0:
            print(f"{item['source_key']}: {item.get('status', 'healthy')} recent={item['recent_count']} latest={item.get('recent_latest')}")
        else:
            print(
                f"{item['source_key']}: {item.get('status', 'unknown')} recent=0 wide={item.get('wide_count', 0)} "
                f"wide_latest={item.get('wide_latest')}"
            )

    print("")
    print(f"[SAVED] {output_path}")
    print(f"[LATEST] {latest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
