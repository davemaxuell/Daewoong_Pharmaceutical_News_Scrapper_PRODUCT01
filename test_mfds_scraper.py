#!/usr/bin/env python
# Test MFDS Scraper with different feed groups

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from scrapers.mfds_scraper import MFDSScraper

print("="*60)
print("MFDS Scraper Test - Main Feeds (7 days)")
print("="*60)

# Test with main feeds
scraper = MFDSScraper(feeds="main")
articles = scraper.fetch_news(days_back=7)

print(f"\n[Main] Total: {len(articles)} articles")
for i, a in enumerate(articles[:5], 1):
    date = a.published.strftime('%Y-%m-%d') if a.published else 'N/A'
    print(f"  {i}. [{date}] {a.source}: {a.title[:40]}...")

print("\n" + "="*60)
print("Testing Safety Feeds")
print("="*60)

# Test safety feeds
scraper2 = MFDSScraper(feeds="safety")
articles2 = scraper2.fetch_news(days_back=7)
print(f"[Safety] Total: {len(articles2)} articles")

print("\n" + "="*60)
print("Testing Regulation Feeds")
print("="*60)

# Test regulation feeds
scraper3 = MFDSScraper(feeds="regulation")
articles3 = scraper3.fetch_news(days_back=7)
print(f"[Regulation] Total: {len(articles3)} articles")
