# Pipeline Improvement Guide

This guide focuses on two goals:

1. Make daily operation safer and more observable.
2. Make adding a new source scraper much faster.

## 1) Runtime Config Overrides

`src/multi_source_scraper.py` now supports optional source overrides from:

- `config/scraper_sources.json`

Base defaults stay in code (`SCRAPERS_CONFIG`), and the JSON file can override:

- `enabled`
- `description`
- `args`
- `use_internal_days_back`

Example:

```json
{
  "pmda": { "enabled": false },
  "mfds": { "args": { "feeds": "main" } }
}
```

Reference template:

- `config/scraper_sources.example.json`

## 2) New Scraper Generator

Use this command to create a new scraper skeleton:

```bash
python scripts/new_scraper.py --key my_source --display-name "My Source" --base-url "https://example.com"
```

This creates:

- `scrapers/my_source_scraper.py`

Then:

1. Implement `fetch_news()`.
2. Import the class in `src/multi_source_scraper.py`.
3. Add a `SCRAPERS_CONFIG` entry.
4. Run validation script.

## 3) Pipeline Validation Script

Run before push/deploy:

```bash
python scripts/validate_pipeline.py
```

Checks:

- Python compile for core modules.
- Keyword/team definition non-empty sanity checks.
- `scraper_sources.json` key/field validation.

## 4) Recommended Next Improvements

1. Move full source registry to `config/sources/*.json` (class name + args), then load dynamically.
2. Add per-scraper contract tests with saved HTML fixtures.
3. Add monitoring metrics:
   - articles scraped per source
   - filter drop rate
   - summary failure rate
   - email send success rate
4. Add CI job:
   - run `scripts/validate_pipeline.py`
   - run scraper unit tests
5. Add dead-letter queue for failed articles (JSONL with retry metadata).

