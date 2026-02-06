#!/usr/bin/env python
# Test PMDA Newsletter Scraper

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from scrapers.pmda_scraper import PMDAScraper

scraper = PMDAScraper()

print("="*60)
print("Testing PMDA Newsletter Scraper")
print(f"URL: {scraper.page_url}")
print("="*60)

articles = scraper.fetch_news(days_back=365, max_pdfs=5)

print(f"\nTotal: {len(articles)} PDFs\n")
for i, a in enumerate(articles[:5], 1):
    date = a.published.strftime('%Y-%m-%d') if a.published else 'N/A'
    print(f"{i}. [{date}] {a.title[:50]}")
    print(f"   PDF: {a.link}")
    print()
