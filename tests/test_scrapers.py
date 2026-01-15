#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test individual scrapers
Usage: python tests/test_scrapers.py --source kpa_news
       python tests/test_scrapers.py --list
       python tests/test_scrapers.py --all
"""

import sys
import os
import argparse
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.multi_source_scraper import MultiSourceScraper


def test_single_scraper(source_name: str, days_back: int = 1):
    """Test a single scraper"""
    print(f"\n{'='*60}")
    print(f"Testing Scraper: {source_name.upper()}")
    print(f"{'='*60}")
    
    config = MultiSourceScraper.SCRAPERS_CONFIG.get(source_name)
    if not config:
        print(f"[ERROR] Unknown source: {source_name}")
        print("Use --list to see available sources")
        return False
    
    print(f"Description: {config['description']}")
    print(f"Enabled: {config.get('enabled', True)}")
    print(f"Days back: {days_back}")
    print("-" * 40)
    
    try:
        scraper_class = config["class"]
        scraper_args = config.get("args", {})
        scraper = scraper_class(**scraper_args)
        
        start_time = datetime.now()
        articles = scraper.fetch_news(days_back=days_back)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n[SUCCESS] Collected {len(articles)} articles in {elapsed:.2f}s")
        
        if articles:
            print("\nSample articles:")
            for i, article in enumerate(articles[:3], 1):
                title = article.title[:60] + "..." if len(article.title) > 60 else article.title
                print(f"  {i}. {title}")
                print(f"     Source: {article.source}")
                print(f"     Classifications: {article.classifications}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_sources():
    """List all available sources"""
    print("\n" + "="*60)
    print("Available Scrapers")
    print("="*60)
    
    for key, config in MultiSourceScraper.SCRAPERS_CONFIG.items():
        status = "✓ Enabled" if config.get("enabled", True) else "✗ Disabled"
        print(f"\n  {key}")
        print(f"    {config['description']}")
        print(f"    [{status}]")


def test_all_scrapers(days_back: int = 1):
    """Test all enabled scrapers"""
    print("\n" + "="*60)
    print("Testing All Scrapers")
    print("="*60)
    
    results = {}
    
    for key, config in MultiSourceScraper.SCRAPERS_CONFIG.items():
        if config.get("enabled", True):
            results[key] = test_single_scraper(key, days_back)
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for key, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {key}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test scrapers")
    parser.add_argument("--source", "-s", help="Specific source to test")
    parser.add_argument("--list", "-l", action="store_true", help="List available sources")
    parser.add_argument("--all", "-a", action="store_true", help="Test all enabled scrapers")
    parser.add_argument("--days", "-d", type=int, default=1, help="Days back to scrape")
    
    args = parser.parse_args()
    
    if args.list:
        list_sources()
    elif args.all:
        test_all_scrapers(args.days)
    elif args.source:
        test_single_scraper(args.source, args.days)
    else:
        print("Usage:")
        print("  python tests/test_scrapers.py --list")
        print("  python tests/test_scrapers.py --source kpa_news")
        print("  python tests/test_scrapers.py --all")
