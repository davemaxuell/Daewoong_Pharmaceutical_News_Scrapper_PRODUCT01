#!/usr/bin/env python
# Test HTML Change Monitor

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from html_change_monitor import RegulatoryPageMonitor

monitor = RegulatoryPageMonitor()
results = monitor.check_all()

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for r in results:
    status = "CHANGED" if r.get("has_changes") else "OK" if r.get("status") != "first_check" else "BASELINE"
    print(f"  [{status}] {r.get('page_name')}: {r.get('description')}")
