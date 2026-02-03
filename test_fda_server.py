#!/usr/bin/env python3
# Test script for FDA Warning Letters scraper
import sys
sys.path.insert(0, 'src')

from scrapers.fda_warning_letters_scraper import FDAWarningLettersScraper

print("Testing FDA Warning Letters Scraper...")
print("=" * 50)

s = FDAWarningLettersScraper(centers=['CDER'])
articles = s.fetch_news(days_back=14)

print(f"\n=== Found {len(articles)} articles ===")

if articles:
    a = articles[0]
    print(f"\nFirst article:")
    print(f"  Title: {a.title}")
    print(f"  Link: {a.link}")
    print(f"  Full text length: {len(a.full_text)} chars")
    print(f"\n  Full text preview (first 500 chars):")
    print("-" * 40)
    print(a.full_text[:500])
    print("-" * 40)
else:
    print("No articles found")
