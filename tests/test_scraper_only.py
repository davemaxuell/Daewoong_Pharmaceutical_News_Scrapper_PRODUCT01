#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Scraper + Monitor 테스트 (AI 요약 및 이메일 발송 제외)
전체 수집 파이프라인의 정상 작동 여부를 빠르게 확인합니다.

Usage:
  python tests/test_scraper_only.py                # 스크래퍼 + 모니터 전체 실행
  python tests/test_scraper_only.py --scraper      # 스크래퍼만 실행
  python tests/test_scraper_only.py --monitor      # 모니터만 실행
  python tests/test_scraper_only.py --days 3       # 3일치 수집
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))


def run_scrapers(days_back: int = 1):
    """모든 스크래퍼 실행 (AI 요약 없이)"""
    print("\n" + "=" * 60)
    print("PHASE 1: NEWS SCRAPERS TEST")
    print(f"Days back: {days_back}")
    print("=" * 60)

    from src.multi_source_scraper import MultiSourceScraper

    scraper = MultiSourceScraper()
    start_time = datetime.now()
    all_results = scraper.fetch_all(days_back=days_back)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Summary
    print("\n" + "-" * 60)
    print(f"SCRAPER RESULTS (completed in {elapsed:.1f}s)")
    print("-" * 60)

    source_stats = {}
    for article in all_results:
        src = article.get("source", "Unknown")
        source_stats[src] = source_stats.get(src, 0) + 1

    for src, count in sorted(source_stats.items(), key=lambda x: -x[1]):
        status = "OK" if count > 0 else "--"
        print(f"  [{status}] {src}: {count}")

    print(f"\n  TOTAL: {len(all_results)} articles")
    return all_results


def run_monitors():
    """모든 모니터 실행 (AI 분석 없이)"""
    print("\n" + "=" * 60)
    print("PHASE 2: MONITORS TEST")
    print("=" * 60)

    results = {}

    # 1. ICH Guidelines
    print("\n[1] ICH Guidelines Monitor...")
    try:
        from src.ich_monitor import ICHGuidelinesMonitor
        monitor = ICHGuidelinesMonitor()
        ich_results = monitor.check_all()
        changes = sum(1 for r in ich_results if r.get("has_changes"))
        results["ICH Guidelines"] = {"status": "ok", "changes": changes}
        print(f"  -> {changes} categories with changes")
    except Exception as e:
        results["ICH Guidelines"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # 2. PMDA Newsletter
    print("\n[2] PMDA Newsletter...")
    try:
        from scrapers.pmda_scraper import PMDAScraper
        pmda = PMDAScraper()
        pmda_articles = pmda.fetch_news(days_back=365, max_pdfs=2)
        results["PMDA Newsletter"] = {"status": "ok", "pdfs": len(pmda_articles)}
        print(f"  -> {len(pmda_articles)} PDFs found")
    except Exception as e:
        results["PMDA Newsletter"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # 3. USP Pending Monographs
    print("\n[3] USP Pending Monographs...")
    try:
        from scrapers.usp_monograph_scraper import USPMonographScraper
        usp = USPMonographScraper()
        usp_articles = usp.fetch_news(days_back=30)
        results["USP Pending"] = {"status": "ok", "articles": len(usp_articles)}
        print(f"  -> {len(usp_articles)} monographs found")
    except Exception as e:
        results["USP Pending"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # 4. EudraLex Volume 4
    print("\n[4] EudraLex Volume 4 (EU GMP)...")
    try:
        from src.eudralex_monitor import EudraLexMonitor
        eudralex = EudraLexMonitor()
        eudralex_result = eudralex.check()
        has_changes = eudralex_result.get("has_changes", False)
        results["EudraLex V4"] = {"status": "ok", "changes": has_changes}
        print(f"  -> Changes: {has_changes}")
    except Exception as e:
        results["EudraLex V4"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # 5. GMP Journal Annex 1
    print("\n[5] GMP Journal Annex 1...")
    try:
        from src.gmpjournal_annex1_monitor import GMPJournalAnnex1Monitor
        annex1 = GMPJournalAnnex1Monitor()
        annex1_result = annex1.check()
        has_changes = annex1_result.get("has_changes", False)
        results["GMP Journal Annex1"] = {"status": "ok", "changes": has_changes}
        print(f"  -> Changes: {has_changes}")
    except Exception as e:
        results["GMP Journal Annex1"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # 6. HTML Page Monitor
    print("\n[6] HTML Page Monitor...")
    try:
        from src.html_change_monitor import RegulatoryPageMonitor
        html_monitor = RegulatoryPageMonitor()
        html_results = html_monitor.check_all()
        changes = sum(1 for r in html_results if r.get("has_changes"))
        results["HTML Monitor"] = {"status": "ok", "changes": changes}
        print(f"  -> {changes} pages with changes")
    except Exception as e:
        results["HTML Monitor"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # Summary
    print("\n" + "-" * 60)
    print("MONITOR RESULTS")
    print("-" * 60)
    for name, result in results.items():
        if result.get("status") == "error":
            print(f"  [FAIL] {name}: {result.get('error', '')[:50]}")
        else:
            print(f"  [ OK ] {name}: {result}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Scraper + Monitor Test (no AI / no email)"
    )
    parser.add_argument("--scraper", action="store_true", help="Run scrapers only")
    parser.add_argument("--monitor", action="store_true", help="Run monitors only")
    parser.add_argument("--days", "-d", type=int, default=1, help="Days back (default: 1)")
    args = parser.parse_args()

    print("=" * 60)
    print("Pharmaceutical News Agent - Test Run")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Mode: Scraper + Monitor ONLY (no AI, no email)")
    print("=" * 60)

    if args.scraper:
        run_scrapers(args.days)
    elif args.monitor:
        run_monitors()
    else:
        run_scrapers(args.days)
        run_monitors()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
