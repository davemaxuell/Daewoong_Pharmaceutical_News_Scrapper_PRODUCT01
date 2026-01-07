# USP Scraper Test - Revision Bulletins with GPT Analysis
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.usp_monograph_scraper import USPMonographScraper

if __name__ == "__main__":
    scraper = USPMonographScraper()
    
    print("=" * 60)
    print("USP Revision Bulletin - GPT Analysis Test")
    print("=" * 60)
    
    # 최신 Revision Bulletin 가져와서 GPT로 분석
    result = scraper.fetch_latest_bulletin_and_analyze()
    
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
    else:
        print("\n" + "=" * 60)
        print("ANALYSIS RESULT")
        print("=" * 60)
        print(f"\nTitle: {result.get('title', 'N/A')}")
        print(f"Official Date: {result.get('official_date', 'N/A')}")
        print(f"PDF: {result.get('pdf_url', 'N/A')}")
        print("\n" + "-" * 60)
        print("GPT Analysis:")
        print("-" * 60)
        print(result.get('analysis', 'No analysis available'))
