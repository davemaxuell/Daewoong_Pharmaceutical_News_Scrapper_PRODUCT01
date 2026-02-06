#!/usr/bin/env python
# Test MFDS RSS feeds availability

import sys
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import requests

# RSS feeds from mfds_scraper.py
RSS_FEEDS = {
    "notice": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0003",
    "announcement": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0004",
    "admin_notice": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0009",
    "public_service": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0013",
    "local_busan": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=2",
    "local_gyeongin": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=3",
    "local_daegu": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=4",
    "local_gwangju": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=5",
    "local_daejeon": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=6",
    "local_seoul": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=7",
    "press_release": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0021",
    "press_explain": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0022",
    "card_news": "http://www.mfds.go.kr/www/rss/brd.do?brdId=card0001",
    "drug_sanction": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0117",
    "device_sanction": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0168",
    "bio_sanction": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0138",
    "test_lab_sanction": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0039",
    "device_recall": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0139",
    "foreign_drug_risk": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0018",
    "safety_letter": "http://www.mfds.go.kr/www/rss/brd.do?brdId=seohan001",
    "recent_laws": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0008",
    "notification": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0005",
    "directive": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0006",
    "regulation": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0007",
    "law_status": "http://www.mfds.go.kr/www/rss/brd.do?brdId=relaw0001",
    "law_decree": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0003",
    "foreign_law": "http://www.mfds.go.kr/www/rss/brd.do?brdId=food0001",
    "civil_guide": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0011",
    "guideline": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0013",
    "official_guide": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0010",
    "test_method": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0065",
    "discussion": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0014",
    "forms": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0015",
    "edu_materials": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0019",
    "special_materials": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0020",
    "video_materials": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0021",
    "general_materials": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0018",
    "personnel": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0087",
    "ntc0056": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0056",
    "ntc0063": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0063",
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

print("="*60)
print("MFDS RSS Feed Availability Test")
print("="*60)

ok_count = 0
fail_count = 0
failed = []

for name, url in RSS_FEEDS.items():
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and '<item>' in r.text:
            print(f"  [OK] {name}")
            ok_count += 1
        else:
            print(f"  [EMPTY] {name} - No items")
            fail_count += 1
            failed.append(name)
    except Exception as e:
        print(f"  [FAIL] {name} - {e}")
        fail_count += 1
        failed.append(name)

print("\n" + "="*60)
print(f"SUMMARY: {ok_count} OK / {fail_count} Failed or Empty")
if failed:
    print(f"Failed feeds: {', '.join(failed)}")
print("="*60)
