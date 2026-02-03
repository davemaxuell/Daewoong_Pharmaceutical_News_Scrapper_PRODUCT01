# 약업신문 (Yakup) 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
import time
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class YakupScraper(BaseScraper):
    """
    약업신문 (Yakup) 뉴스 스크래퍼

    수집 소스 (3개):
    1. https://www.yakup.com/news/index.html (메인 뉴스)
    2. https://www.yakup.com/news/index.html?cat=11 (카테고리 11)
    3. https://www.yakup.com/news/index.html?cat=12&cat2=121 (카테고리 12, 서브카테고리 121)
    """

    # 타겟 카테고리 URLs
    TARGET_CATEGORIES = [
        "/news/index.html",                    # 메인 뉴스
        "/news/index.html?cat=11",             # 카테고리 11
        "/news/index.html?cat=12&cat2=121",    # 카테고리 12, 서브카테고리 121
    ]

    @property
    def source_name(self) -> str:
        return "Yakup"

    @property
    def base_url(self) -> str:
        return "https://www.yakup.com"

    @property
    def list_url(self) -> str:
        """메인 뉴스 목록 URL"""
        return f"{self.base_url}/news/index.html"
    
    def _get_search_url(self, query: str) -> str:
        """검색 URL 생성 (뉴스 타입으로 필터)"""
        # 공백을 "+"로 대체
        encoded_query = query.replace(" ", "+")
        return f"{self.base_url}/search/index.html?csearch_word={encoded_query}&csearch_type=news"
    
    def _get_days_back(self) -> int:
        """
        요일에 따른 수집 기간 결정
        월요일: 3일 (주말 포함)
        평일: 1일
        """
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return 3
        return 1

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        약업신문에서 뉴스 수집 (3개 카테고리)

        Args:
            query: 검색 키워드 (None이면 카테고리별 수집)
            days_back: 수집 기간 (None이면 자동 계산)

        Returns:
            NewsArticle 리스트 (keywords.py로 분류된 기사만)
        """
        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)
        print(f"[Yakup] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")

        articles = []
        seen_links = set()  # 중복 방지

        # query가 있으면 검색, 없으면 카테고리별 수집
        if query:
            url = self._get_search_url(query)
            print(f"\n[Yakup] === Searching: '{query}' ===")
            category_articles = self._scrape_category_page(url, cutoff_date, "Search")
            for article in category_articles:
                if article.link not in seen_links:
                    articles.append(article)
                    seen_links.add(article.link)
        else:
            # 각 카테고리에서 수집
            for category_path in self.TARGET_CATEGORIES:
                url = f"{self.base_url}{category_path}"
                category_name = self._get_category_name(category_path)
                print(f"\n[Yakup] === Scraping category: {category_name} ===")
                category_articles = self._scrape_category_page(url, cutoff_date, category_name)
                for article in category_articles:
                    if article.link not in seen_links:
                        articles.append(article)
                        seen_links.add(article.link)

        print(f"\n[Yakup] Total collected: {len(articles)} articles from {len(self.TARGET_CATEGORIES)} sources")
        return articles

    def _get_category_name(self, category_path: str) -> str:
        """카테고리 경로에서 이름 추출"""
        if "cat=11" in category_path:
            return "Cat-11"
        elif "cat=12" in category_path:
            return "Cat-12-121"
        else:
            return "Main"

    def _scrape_category_page(self, url: str, cutoff_date: datetime, category_name: str) -> List[NewsArticle]:
        """카테고리 페이지에서 기사 수집"""
        articles = []

        # 재시도 로직 (최대 3회)
        soup = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                print(f"[Yakup {category_name}] Fetching: {url}")
                time.sleep(1)  # Rate limiting
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                response.encoding = 'utf-8'

                if response.status_code != 200:
                    print(f"[Yakup {category_name}] HTTP error: {response.status_code}")
                    return articles

                soup = BeautifulSoup(response.text, 'html.parser')
                break

            except requests.exceptions.Timeout:
                print(f"[Yakup {category_name}] Timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"[Yakup {category_name}] Max retries exceeded")
                    return articles
            except Exception as e:
                print(f"[Yakup {category_name}] Request failed: {e}")
                return articles

        if soup is None:
            return articles

        # 기사 목록 파싱 - mode=view 포함하는 링크
        article_links = soup.select('a[href*="mode=view"]')
        print(f"[Yakup {category_name}] Found {len(article_links)} article links")

        for link_tag in article_links:
            try:
                article = self._parse_article_item(link_tag, cutoff_date, category_name)
                if article:
                    articles.append(article)
            except Exception as e:
                continue

        print(f"[Yakup {category_name}] Collected {len(articles)} articles")
        return articles
    
    # Yakup 본문 CSS 선택자
    CONTENT_SELECTORS = ['.article_body', '.view_cont', '.news_body', '#articleBody']

    def _parse_article_item(self, link_tag, cutoff_date: datetime, category_name: str = None) -> NewsArticle | None:
        """개별 기사 아이템 파싱 + 본문 수집"""
        href = link_tag.get('href', '')
        
        # 절대 URL 생성
        if href.startswith('/'):
            full_link = f"{self.base_url}{href}"
        else:
            full_link = href
        
        # 제목 (.title_con span)
        title_elem = link_tag.select_one('.title_con span')
        title = title_elem.get_text(strip=True) if title_elem else ''
        
        if not title:
            return None
        
        # 요약 (.text_con span)
        summary_elem = link_tag.select_one('.text_con span')
        summary = summary_elem.get_text(strip=True) if summary_elem else ''
        
        # 날짜 (.name_con span) - Format: YYYY-MM-DD HH:MM
        date_elem = link_tag.select_one('.name_con span')
        date_text = date_elem.get_text(strip=True) if date_elem else ''
        
        # 날짜 파싱
        published = self._parse_date(date_text)
        
        # 날짜 필터링
        if published and published >= cutoff_date:
            classifications, matched_keywords = classify_article(title, summary)

            # Add category to classifications
            if category_name and category_name not in classifications:
                classifications.append(f"Yakup-{category_name}")

            # 본문 수집
            content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)

            # Build title with category prefix
            title_prefix = "[약업신문]"
            if category_name and category_name != "Main":
                title_prefix = f"[약업신문 - {category_name}]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=full_link,
                published=published,
                source=self.source_name,
                summary=summary,
                full_text=content.get("full_text", "")[:10000] if content.get("full_text") else "",
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )
        elif not published:
            # 날짜가 없는 경우에도 수집
            classifications, matched_keywords = classify_article(title, summary)

            # Add category to classifications
            if category_name and category_name not in classifications:
                classifications.append(f"Yakup-{category_name}")

            # 본문 수집
            content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)

            # Build title with category prefix
            title_prefix = "[약업신문]"
            if category_name and category_name != "Main":
                title_prefix = f"[약업신문 - {category_name}]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=full_link,
                published=None,
                source=self.source_name,
                summary=summary,
                full_text=content.get("full_text", "")[:10000] if content.get("full_text") else "",
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )

        return None
    
    def _parse_date(self, date_text: str) -> datetime | None:
        """날짜 문자열 파싱"""
        if not date_text:
            return None
        
        formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        return None
