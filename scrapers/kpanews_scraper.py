# 약사공론 (KPA News) 스크래퍼
# RSS 피드 기반으로 변경 (2026-02 사이트 리뉴얼 대응)

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import time
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class KPANewsScraper(BaseScraper):
    """
    약사공론 (KPA News) 뉴스 스크래퍼

    RSS 피드 기반 수집:
    - https://cdn.kpanews.co.kr/rss/gn_rss_allArticle.xml
    """

    RSS_URL = "https://cdn.kpanews.co.kr/rss/gn_rss_allArticle.xml"

    @property
    def source_name(self) -> str:
        return "KPA News"

    @property
    def base_url(self) -> str:
        return "https://www.kpanews.co.kr"

    def _get_days_back(self) -> int:
        """
        요일에 따른 수집 기간 결정
        - 월요일: 3일 (금~일 포함)
        - 그 외: 1일
        """
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return 3
        return 1

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        약사공론에서 RSS 피드로 뉴스 수집

        Args:
            query: 검색 키워드 (RSS에서는 제목/요약 필터링으로 사용)
            days_back: 수집 기간 (None이면 자동 계산: 1일 / 월요일 3일)

        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)

        print(f"[KPA] Fetching RSS feed (days_back: {days_back})")
        print(f"[KPA] Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")

        try:
            # RSS 피드 파싱
            feed = feedparser.parse(self.RSS_URL)

            if feed.bozo:
                print(f"[KPA] RSS parse warning: {feed.bozo_exception}")

            print(f"[KPA] Found {len(feed.entries)} entries in RSS feed")

        except Exception as e:
            print(f"[KPA] RSS fetch error: {e}")
            return []

        articles = []

        for entry in feed.entries:
            try:
                article = self._parse_rss_entry(entry, cutoff_date, query)
                if article:
                    articles.append(article)
            except Exception as e:
                print(f"[KPA] Error parsing entry: {e}")
                continue

        print(f"[KPA] Collected {len(articles)} articles")
        return articles

    # KPANews 본문 CSS 선택자
    CONTENT_SELECTORS = ['#articleBody', '.article-body', '.article_body', '.news_body', '.article-content']

    def _parse_rss_entry(self, entry, cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """RSS 엔트리 파싱"""
        # 제목
        title = entry.get('title', '').strip()
        if not title:
            return None

        # 링크
        link = entry.get('link', '')
        if not link:
            return None

        # 날짜 파싱
        published = None
        if entry.get('published_parsed'):
            try:
                published = datetime(*entry.published_parsed[:6])
            except:
                pass

        # 날짜 필터링
        if published and published < cutoff_date:
            return None

        # 날짜 없으면 스킵
        if not published:
            print(f"[KPA] No date found - skipping: {title[:50]}...")
            return None

        # 요약
        summary = entry.get('summary', '')
        if summary:
            # HTML 태그 제거
            soup = BeautifulSoup(summary, 'html.parser')
            summary = soup.get_text(strip=True)

        # 쿼리 필터링 (있는 경우)
        if query:
            query_lower = query.lower()
            if query_lower not in title.lower() and query_lower not in summary.lower():
                return None

        # 분류
        classifications, matched_keywords = classify_article(title, summary)
        if not classifications:
            classifications = ["업계뉴스"]
            matched_keywords = []

        # 본문 수집
        content = self.fetch_article_content(link, self.CONTENT_SELECTORS)

        return NewsArticle(
            title=title,
            link=link,
            published=published,
            source=self.source_name,
            summary=summary[:300] if summary else "",
            full_text=content.get("full_text", ""),
            images=content.get("images", []),
            scrape_status=content.get("status", "pending"),
            classifications=classifications,
            matched_keywords=matched_keywords
        )


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KPA News Scraper")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 1 day or 3 on Monday)")
    args = parser.parse_args()

    scraper = KPANewsScraper()

    print("=" * 60)
    print("KPA News (약사공론) Scraper")
    print("=" * 60)

    articles = scraper.fetch_news(query=args.query, days_back=args.days)

    print(f"\nTotal collected: {len(articles)} articles\n")

    for i, article in enumerate(articles[:15], 1):
        date_str = article.published.strftime('%Y-%m-%d %H:%M') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:50]}...")
        print(f"   Link: {article.link}")
        print()
