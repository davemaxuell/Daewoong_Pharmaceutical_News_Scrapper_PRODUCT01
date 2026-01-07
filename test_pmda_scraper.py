# PMDA Scraper Test - GPT Summary
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.pmda_scraper import PMDAScraper

if __name__ == "__main__":
    scraper = PMDAScraper()
    
    print("=" * 60)
    print("PMDA Updates - GPT Summary Test")
    print("=" * 60)
    
    # 최신 Update 가져와서 GPT로 요약
    result = scraper.fetch_latest_and_summarize()
    
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
    else:
        print("\n" + "=" * 60)
        print("SUMMARY RESULT")
        print("=" * 60)
        print(f"\nTitle: {result.get('title', 'N/A')}")
        print(f"Date: {result.get('published_date', 'N/A')}")
        print(f"PDF: {result.get('pdf_url', 'N/A')}")
        print("\n" + "-" * 60)
        print("GPT Summary:")
        print("-" * 60)
        print(result.get('summary', 'No summary available'))
