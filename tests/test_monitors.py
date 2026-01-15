#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test monitors (ICH, HTML change detection)
Usage: python tests/test_monitors.py --ich
       python tests/test_monitors.py --html
       python tests/test_monitors.py --all
"""

import sys
import os
import argparse
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))


def test_ich_monitor():
    """Test ICH Guidelines Monitor"""
    print("\n" + "="*60)
    print("Testing ICH Guidelines Monitor")
    print("="*60)
    
    try:
        from src.ich_monitor import ICHGuidelinesMonitor
        
        monitor = ICHGuidelinesMonitor()
        
        print("\nChecking ICH categories...")
        start_time = datetime.now()
        results = monitor.check_all()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n[SUCCESS] Check completed in {elapsed:.2f}s")
        
        changes_found = 0
        for res in results:
            has_changes = res.get("has_changes", False)
            status = "📢 CHANGES" if has_changes else "✓ No changes"
            print(f"  {status}: {res.get('category', 'Unknown')}")
            if has_changes:
                changes_found += 1
                new_links = res.get("new_links", [])
                for link in new_links[:3]:
                    print(f"    -> {link[:60]}...")
        
        print(f"\nTotal: {len(results)} categories checked, {changes_found} with changes")
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_monitor():
    """Test HTML Change Monitor"""
    print("\n" + "="*60)
    print("Testing HTML Change Monitor")
    print("="*60)
    
    try:
        from src.html_change_monitor import EudraLexMonitor, PMDAJPMonitor
        
        # Test EudraLex
        print("\n[1] Testing EudraLex Monitor...")
        eudralex = EudraLexMonitor()
        result = eudralex.check()
        
        if result.get("error"):
            print(f"  [WARN] EudraLex error: {result.get('error')}")
        else:
            print(f"  [SUCCESS] EudraLex checked")
            print(f"    Has changes: {result.get('has_changes', False)}")
        
        # Test PMDA JP
        print("\n[2] Testing PMDA JP Monitor...")
        pmda = PMDAJPMonitor()
        result = pmda.check_jp18()
        
        if result.get("error"):
            print(f"  [WARN] PMDA error: {result.get('error')}")
        else:
            print(f"  [SUCCESS] PMDA JP18 checked")
            print(f"    Has changes: {result.get('has_changes', False)}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_monitors():
    """Test all monitors"""
    results = {
        "ICH Monitor": test_ich_monitor(),
        "HTML Monitor": test_html_monitor()
    }
    
    print("\n" + "="*60)
    print("Monitor Test Summary")
    print("="*60)
    
    for name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test monitors")
    parser.add_argument("--ich", action="store_true", help="Test ICH monitor")
    parser.add_argument("--html", action="store_true", help="Test HTML monitor")
    parser.add_argument("--all", "-a", action="store_true", help="Test all monitors")
    
    args = parser.parse_args()
    
    if args.ich:
        test_ich_monitor()
    elif args.html:
        test_html_monitor()
    elif args.all:
        test_all_monitors()
    else:
        print("Usage:")
        print("  python tests/test_monitors.py --ich")
        print("  python tests/test_monitors.py --html")
        print("  python tests/test_monitors.py --all")
