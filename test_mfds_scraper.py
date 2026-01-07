# MFDS RSS Scraper Test
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.mfds_scraper import MFDSScraper

if __name__ == "__main__":
    # 사용 가능한 피드 목록 출력
    MFDSScraper.list_available_feeds()
    
    print("\n" + "=" * 60)
    print("MFDS RSS Scraper - Main Feeds Test")
    print("=" * 60)
    
    # 주요 피드에서 수집
    scraper = MFDSScraper(feeds="main")
    articles = scraper.fetch_news(days_back=7)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:15], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:50]}...")
        print(f"   Source: {article.source}")
        print(f"   Link: {article.link}")
        print()
