#!/usr/bin/env python
# Test USP Pending Monograph Scraper

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from scrapers.usp_monograph_scraper import USPMonographScraper

scraper = USPMonographScraper()

print("="*60)
print("1. Testing Pending Monographs")
print("="*60)
articles = scraper.fetch_news(days_back=60)
print(f"\nTotal Pending Monographs: {len(articles)}")
for i, a in enumerate(articles[:5], 1):
    date = a.published.strftime('%Y-%m-%d') if a.published else 'N/A'
    print(f"\n{i}. [{date}] {a.title[:60]}")
    print(f"   PDF: {a.link}")

print("\n" + "="*60)
print("2. Testing Revision Bulletins")
print("="*60)
bulletins = scraper.fetch_revision_bulletins(days_back=60)
print(f"\nTotal Revision Bulletins: {len(bulletins)}")
for i, a in enumerate(bulletins[:5], 1):
    date = a.published.strftime('%Y-%m-%d') if a.published else 'N/A'
    print(f"\n{i}. [{date}] {a.title[:60]}")
    print(f"   PDF: {a.link}")
