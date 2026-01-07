# KPBMA Newsletter Scraper Test
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.kpbma_scraper import KPBMAScraper

if __name__ == "__main__":
    scraper = KPBMAScraper()
    
    print("=" * 60)
    print("KPBMA Newsletter Scraper Test")
    print("=" * 60)
    
    # 30일 테스트 (더 많은 뉴스레터 포함)
    articles = scraper.fetch_news(days_back=30)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:15], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:50]}...")
        print(f"   Source: {article.source}")
        print(f"   Link: {article.link[:60]}...")
        print()
