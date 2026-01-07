# KPA News Scraper Test
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.kpanews_scraper import KPANewsScraper

if __name__ == "__main__":
    scraper = KPANewsScraper()
    
    print("=" * 60)
    print("KPA News (약사공론) Scraper Test")
    print("=" * 60)
    
    # 1일 기준 테스트
    articles = scraper.fetch_news(days_back=1)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:15], 1):
        date_str = article.published.strftime('%Y-%m-%d %H:%M') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:50]}...")
        print(f"   Link: {article.link}")
        print()
