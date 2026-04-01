"""Generate team-to-keyword data from config team/category files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEAM_EMAILS = PROJECT_ROOT / "config" / "team_emails.json"
DEFAULT_UPDATED_KEYWORDS = PROJECT_ROOT / "config" / "updated_keywords.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "config" / "team_keyword_data.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team-emails", default=str(DEFAULT_TEAM_EMAILS), help="Path to team_emails.json")
    parser.add_argument(
        "--updated-keywords",
        default=str(DEFAULT_UPDATED_KEYWORDS),
        help="Path to updated_keywords.json",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to output JSON file")
    return parser


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value:
            continue
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def normalize_category_name(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def build_category_keyword_map(updated_keywords: dict) -> dict[str, list[str]]:
    category_map: dict[str, list[str]] = {}
    terminology = updated_keywords.get("pharmaceutical_terminology", {})
    for raw_item in terminology.values():
        item = raw_item if isinstance(raw_item, dict) else {}
        category_names = unique_preserve_order(
            [
                str(((item.get("category_name") or {}).get("ko")) or "").strip(),
                str(((item.get("category_name") or {}).get("en")) or "").strip(),
            ]
        )
        if not category_names:
            continue

        all_terms: list[str] = []
        for raw_term_group in item.get("terms", []) or []:
            term_group = raw_term_group if isinstance(raw_term_group, dict) else {}
            for bucket in ("en", "ko"):
                values = term_group.get(bucket, []) or []
                for value in values:
                    all_terms.append(str(value or "").strip())

        keywords = unique_preserve_order(all_terms)
        for category_name in category_names:
            category_map[category_name] = keywords
    return category_map


def build_team_keyword_data(
    team_emails: dict,
    category_keyword_map: dict[str, list[str]],
    *,
    team_emails_source: Path,
    updated_keywords_source: Path,
) -> dict:
    teams: dict[str, dict] = {}
    normalized_category_keyword_map = {
        normalize_category_name(category_name): keywords
        for category_name, keywords in category_keyword_map.items()
    }

    for team_key, raw_team_info in team_emails.items():
        team_info = raw_team_info if isinstance(raw_team_info, dict) else {}
        team_name = str(team_info.get("team_name") or team_key or "").strip()
        if not team_name:
            continue

        categories = unique_preserve_order([str(value or "").strip() for value in team_info.get("categories", []) or []])
        category_keywords = {
            category: category_keyword_map.get(category, normalized_category_keyword_map.get(normalize_category_name(category), []))
            for category in categories
        }
        combined_keywords = unique_preserve_order(
            [keyword for keywords in category_keywords.values() for keyword in keywords]
        )

        teams[team_name] = {
            "team_name": team_name,
            "categories": categories,
            "category_keywords": category_keywords,
            "keywords": combined_keywords,
            "missing_categories": [
                category
                for category in categories
                if not category_keywords.get(category)
            ],
            "member_count": len(
                [
                    member
                    for member in (team_info.get("members", []) or [])
                    if str((member or {}).get("email") or "").strip()
                ]
            ),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "team_emails": str(team_emails_source.relative_to(PROJECT_ROOT)),
            "updated_keywords": str(updated_keywords_source.relative_to(PROJECT_ROOT)),
        },
        "teams": teams,
    }


def main() -> int:
    args = build_parser().parse_args()
    team_emails_path = Path(args.team_emails).resolve()
    updated_keywords_path = Path(args.updated_keywords).resolve()
    output_path = Path(args.output).resolve()

    team_emails = load_json(team_emails_path)
    updated_keywords = load_json(updated_keywords_path)
    category_keyword_map = build_category_keyword_map(updated_keywords)
    payload = build_team_keyword_data(
        team_emails,
        category_keyword_map,
        team_emails_source=team_emails_path,
        updated_keywords_source=updated_keywords_path,
    )

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(payload['teams'])} team entries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
