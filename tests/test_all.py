#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run all tests
Usage: python tests/test_all.py
       python tests/test_all.py --quick  (skip slow tests)
"""

import sys
import os
import argparse
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def run_all_tests(quick_mode: bool = False):
    """Run all test suites"""
    print("="*60)
    print("PHARMA NEWS AGENT - FULL TEST SUITE")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    
    # 1. Keywords Test
    print("\n" + "="*60)
    print("[1/6] KEYWORD CLASSIFICATION")
    print("="*60)
    try:
        from tests.test_keywords import test_classification, show_categories
        show_categories()
        test_classification("FDA GMP deviation CAPA 일탈 조사")
        results["Keywords"] = True
    except Exception as e:
        print(f"[FAILED] {e}")
        results["Keywords"] = False
    
    # 2. Teams Test
    print("\n" + "="*60)
    print("[2/6] TEAM ROUTING")
    print("="*60)
    try:
        from tests.test_teams import test_team_definitions, test_team_emails
        test_team_definitions()
        test_team_emails()
        results["Teams"] = True
    except Exception as e:
        print(f"[FAILED] {e}")
        results["Teams"] = False
    
    # 3. API Test
    print("\n" + "="*60)
    print("[3/6] API CONNECTIVITY")
    print("="*60)
    try:
        from tests.test_api import test_gemini_api
        results["Gemini API"] = test_gemini_api()
    except Exception as e:
        print(f"[FAILED] {e}")
        results["Gemini API"] = False
    
    # 4. Email Config Test
    print("\n" + "="*60)
    print("[4/6] EMAIL CONFIGURATION")
    print("="*60)
    try:
        from tests.test_api import test_email_config
        results["Email Config"] = test_email_config()
    except Exception as e:
        print(f"[FAILED] {e}")
        results["Email Config"] = False
    
    # 5. Scrapers Test (slow, skip in quick mode)
    if not quick_mode:
        print("\n" + "="*60)
        print("[5/6] SCRAPERS (testing 1 source)")
        print("="*60)
        try:
            from tests.test_scrapers import test_single_scraper
            results["Scrapers"] = test_single_scraper("kpa_news", days_back=1)
        except Exception as e:
            print(f"[FAILED] {e}")
            results["Scrapers"] = False
    else:
        print("\n[SKIPPED] Scrapers test (quick mode)")
        results["Scrapers"] = "SKIPPED"
    
    # 6. Monitors Test (slow, skip in quick mode)
    if not quick_mode:
        print("\n" + "="*60)
        print("[6/6] MONITORS (testing ICH)")
        print("="*60)
        try:
            from tests.test_monitors import test_ich_monitor
            results["Monitors"] = test_ich_monitor()
        except Exception as e:
            print(f"[FAILED] {e}")
            results["Monitors"] = False
    else:
        print("\n[SKIPPED] Monitors test (quick mode)")
        results["Monitors"] = "SKIPPED"
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v == "SKIPPED")
    
    for name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "○ SKIP"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check output above for details.")
    
    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all tests")
    parser.add_argument("--quick", "-q", action="store_true", 
                       help="Quick mode (skip slow tests)")
    
    args = parser.parse_args()
    
    success = run_all_tests(quick_mode=args.quick)
    sys.exit(0 if success else 1)
