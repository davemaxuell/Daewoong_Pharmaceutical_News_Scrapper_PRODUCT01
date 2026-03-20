"""Source sync utilities."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Source


def ensure_sources_seeded(db: Session) -> None:
    from src.multi_source_scraper import MultiSourceScraper

    scraper = MultiSourceScraper()
    existing_by_code = {s.code: s for s in db.query(Source).all()}

    for source_code, config in scraper.scrapers_config.items():
        scraper_class = config.get("class")
        scraper_module = scraper_class.__module__ if scraper_class else "unknown"
        existing = existing_by_code.get(source_code)
        if existing:
            existing.display_name = config.get("description", source_code)
            existing.scraper_module = scraper_module
            # Keep admin-edited enable values if already present
            if existing.timeout_seconds is None:
                existing.timeout_seconds = 120
            if existing.max_items is None:
                existing.max_items = 200
            continue

        db.add(
            Source(
                code=source_code,
                display_name=config.get("description", source_code),
                scraper_module=scraper_module,
                is_enabled=bool(config.get("enabled", True)),
                timeout_seconds=120,
                max_items=200,
            )
        )
    db.commit()
