#!/usr/bin/env python
# Quick test for PIC/S scraper

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from scrapers.pics_scraper import PICSScraper

scraper = PICSScraper()
articles = scraper.fetch_news(days_back=30)

print(f"\n{'='*60}")
print(f"PIC/S Scraper Test - Total: {len(articles)} articles")
print('='*60)

for i, a in enumerate(articles[:10], 1):
    date = a.published.strftime('%Y-%m-%d') if a.published else 'N/A'
    print(f"\n{i}. [{date}] {a.title[:70]}")
    print(f"   URL: {a.link}")
