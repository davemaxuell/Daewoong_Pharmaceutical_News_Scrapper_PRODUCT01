#!/usr/bin/env python
# Test USP monitoring with Playwright

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from html_change_monitor import RegulatoryPageMonitor

monitor = RegulatoryPageMonitor()

print("="*60)
print("Testing USP Page Monitoring with Playwright")
print("="*60)

# Test only USP pages
for name in ["USP_Pending", "USP_Bulletins"]:
    config = monitor.MONITORED_PAGES[name]
    print(f"\n[Test] {name}: {config['description']}")
    print(f"  URL: {config['url']}")

    result = monitor.check_for_changes(
        config['url'],
        config['selector'],
        use_playwright=config.get('use_playwright', False)
    )

    if result.get("status") == "error":
        print(f"  [ERROR] {result.get('error')}")
    elif result.get("status") == "first_check":
        print(f"  [OK] Baseline saved!")
    else:
        print(f"  [OK] Changes: {result.get('has_changes')}")
