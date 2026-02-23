#!/usr/bin/env python
"""Generate a new scraper skeleton with the project's conventions."""

from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = '''# {display_name} scraper

from datetime import datetime, timedelta
from typing import List, Optional

from .base_scraper import BaseScraper, NewsArticle
from keywords import classify_article


class {class_name}(BaseScraper):
    """Scraper for {display_name}."""

    @property
    def source_name(self) -> str:
        return "{display_name}"

    @property
    def base_url(self) -> str:
        return "{base_url}"

    def fetch_news(self, query: str = None, days_back: int = 1) -> List[NewsArticle]:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        articles: List[NewsArticle] = []

        # TODO: 1) collect article links
        # TODO: 2) parse title, link, published, summary
        # TODO: 3) call classify_article(title, summary)
        # TODO: 4) optionally fetch full text via self.fetch_article_content()

        # Example:
        # title = "..."
        # summary = "..."
        # classifications, matched_keywords = classify_article(title, summary)
        # if not classifications:
        #     return articles
        # articles.append(
        #     NewsArticle(
        #         title=title,
        #         link="...",
        #         published=datetime.now(),
        #         source=self.source_name,
        #         summary=summary,
        #         full_text="",
        #         images=[],
        #         scrape_status="success",
        #         classifications=classifications,
        #         matched_keywords=matched_keywords,
        #     )
        # )

        return articles
'''


def snake_from_key(key: str) -> str:
    return key.strip().lower().replace("-", "_").replace(" ", "_")


def class_from_key(key: str) -> str:
    parts = [p for p in snake_from_key(key).split("_") if p]
    return "".join(p.capitalize() for p in parts) + "Scraper"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a scraper skeleton file.")
    parser.add_argument("--key", required=True, help="Source key, e.g. my_new_source")
    parser.add_argument("--display-name", required=True, help="Human readable source name")
    parser.add_argument("--base-url", required=True, help="Base URL")
    parser.add_argument(
        "--class-name",
        default=None,
        help="Optional explicit class name. Default: <Key>Scraper",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if file already exists",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    key = snake_from_key(args.key)
    class_name = args.class_name or class_from_key(key)
    file_path = project_root / "scrapers" / f"{key}_scraper.py"

    if file_path.exists() and not args.force:
        print(f"[ERROR] File exists: {file_path}")
        print("Use --force to overwrite.")
        return 1

    file_path.write_text(
        TEMPLATE.format(
            class_name=class_name,
            display_name=args.display_name,
            base_url=args.base_url,
        ),
        encoding="utf-8",
    )

    print(f"[OK] Generated: {file_path}")
    print("")
    print("Next steps:")
    print("1. Implement fetch_news() parsing logic in the new scraper.")
    print(f"2. Add import in src/multi_source_scraper.py for {class_name}.")
    print(f"3. Add SCRAPERS_CONFIG entry with key '{key}'.")
    print("4. Run: python scripts/validate_pipeline.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

