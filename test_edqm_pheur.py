#!/usr/bin/env python
# Test EDQM PhEur newsroom

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from scrapers.edqm_scraper import EDQMScraper

scraper = EDQMScraper(newsroom="pheur")

print("="*60)
print("Testing EDQM PhEur Newsroom")
print("="*60)

articles = scraper.fetch_news(days_back=60)

print(f"\nTotal: {len(articles)} articles\n")
for i, a in enumerate(articles[:5], 1):
    date = a.published.strftime('%Y-%m-%d') if a.published else 'N/A'
    print(f"{i}. [{date}] {a.title[:60]}")
    print(f"   URL: {a.link}")
    print()
