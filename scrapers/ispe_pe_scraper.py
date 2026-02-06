# ISPE Pharmaceutical Engineering Magazine Scraper (Login Required)
# ISPE PE 매거진 스크래퍼 - 로그인 필요

import os
import sys
import time
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article, get_all_keywords

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    from base_scraper import BaseScraper, NewsArticle

# Playwright import
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class ISPEPEScraper(BaseScraper):
    """
    ISPE Pharmaceutical Engineering Magazine Scraper

    로그인이 필요한 ISPE PE 매거진 콘텐츠 수집
    Playwright를 사용하여 SSO 로그인 후 콘텐츠 스크래핑

    수집 대상:
    - https://ispe.org/pharmaceutical-engineering
    - 기술 아티클, 케이스 스터디, 인터뷰 등

    수집 규칙:
    - 평일: 1일치 기사 수집
    - 월요일: 3일치 기사 수집 (주말 포함)
    - keywords.py의 키워드와 매칭되는 기사만 수집
    """

    # URLs
    BASE_URL = "https://ispe.org"
    PE_URL = "https://ispe.org/pharmaceutical-engineering"
    LOGIN_URL = "https://my.ispe.org/ISPE/SSO/SignIn.aspx"

    # Credentials (from environment or config)
    DEFAULT_USERNAME = os.getenv("ISPE_USERNAME", "daewoong02")
    DEFAULT_PASSWORD = os.getenv("ISPE_PASSWORD", "daewoong02")

    def __init__(self, username: str = None, password: str = None):
        """
        ISPE PE 스크래퍼 초기화

        Args:
            username: ISPE 로그인 사용자명 (기본값: 환경변수 또는 daewoong02)
            password: ISPE 로그인 비밀번호 (기본값: 환경변수 또는 daewoong02)
        """
        self.username = username or self.DEFAULT_USERNAME
        self.password = password or self.DEFAULT_PASSWORD
        self._browser = None
        self._context = None
        self._page = None

    @property
    def source_name(self) -> str:
        return "ISPE PE Magazine"

    @property
    def base_url(self) -> str:
        return self.BASE_URL

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

    def _login(self, page) -> bool:
        """
        ISPE SSO 로그인

        Args:
            page: Playwright page object

        Returns:
            로그인 성공 여부
        """
        try:
            print(f"[ISPE-PE] Navigating to login page...")
            page.goto(self.LOGIN_URL, timeout=60000, wait_until="networkidle")

            # Wait for login form
            page.wait_for_selector('input[type="text"]', timeout=10000)

            print(f"[ISPE-PE] Entering credentials...")

            # Fill username - find by partial ID match
            username_input = page.locator('input[id*="signInUserName"]')
            username_input.fill(self.username)

            # Fill password
            password_input = page.locator('input[id*="signInPassword"]')
            password_input.fill(self.password)

            # Click submit button
            submit_button = page.locator('input[id*="SubmitButton"]')
            submit_button.click()

            # Wait for redirect after login
            print(f"[ISPE-PE] Waiting for login redirect...")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Check if login was successful (no longer on login page)
            current_url = page.url
            if "SignIn" not in current_url:
                print(f"[ISPE-PE] Login successful!")
                return True
            else:
                print(f"[ISPE-PE] Login may have failed. Current URL: {current_url}")
                return False

        except PlaywrightTimeout:
            print(f"[ISPE-PE] Login timeout")
            return False
        except Exception as e:
            print(f"[ISPE-PE] Login error: {e}")
            return False

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        ISPE PE 매거진에서 기사 수집 (로그인 필요)

        Args:
            query: 검색 키워드 (선택적)
            days_back: 수집 기간 (일수)

        Returns:
            NewsArticle 리스트
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("[ISPE-PE] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return []

        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)
        articles = []

        print(f"[ISPE-PE] Starting scrape (days_back: {days_back})")

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()

                # Login first
                if not self._login(page):
                    print("[ISPE-PE] Login failed. Attempting to scrape public content...")

                # Navigate to PE magazine page
                print(f"[ISPE-PE] Navigating to: {self.PE_URL}")
                page.goto(self.PE_URL, timeout=60000, wait_until="networkidle")

                # Get page content
                content = page.content()

                # Parse with BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')

                # Find article links (adjust selectors based on actual page structure)
                article_links = soup.select('article a, .article-card a, .teaser a, .view-content a')

                print(f"[ISPE-PE] Found {len(article_links)} potential article links")

                seen_urls = set()

                for link in article_links:
                    href = link.get('href', '')
                    if not href or href in seen_urls:
                        continue

                    # Skip non-article links
                    if not href or href.startswith('#') or 'javascript:' in href:
                        continue

                    # Build full URL
                    if href.startswith('/'):
                        full_url = f"{self.BASE_URL}{href}"
                    elif not href.startswith('http'):
                        full_url = f"{self.BASE_URL}/{href}"
                    else:
                        full_url = href

                    # Only process ISPE URLs
                    if 'ispe.org' not in full_url:
                        continue

                    seen_urls.add(full_url)

                    # Get article title
                    title = link.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue

                    # Filter by query if provided
                    if query and query.lower() not in title.lower():
                        continue

                    # Classify article using keywords.py
                    classifications, matched_keywords = classify_article(title, "")

                    # Only add if matches keywords (strict filtering like other scrapers)
                    if not classifications:
                        # Check if title contains any keyword
                        all_keywords = get_all_keywords()
                        title_lower = title.lower()
                        for keyword in all_keywords:
                            if keyword.lower() in title_lower:
                                matched_keywords = [keyword]
                                classifications = ["제약기술"]
                                break

                    # Only add articles that match keywords
                    if classifications and matched_keywords:
                        articles.append(NewsArticle(
                            title=title,
                            link=full_url,
                            published=None,  # Will try to get from article page
                            source=self.source_name,
                            summary="",
                            classifications=classifications,
                            matched_keywords=matched_keywords
                        ))
                        print(f"[ISPE-PE] Added: {title[:50]}...")

                # Optionally fetch article details (can be slow)
                # for article in articles[:10]:  # Limit to avoid rate limiting
                #     self._fetch_article_details(page, article)

                browser.close()

        except Exception as e:
            print(f"[ISPE-PE] Scraping error: {e}")
            import traceback
            traceback.print_exc()

        # Remove duplicates
        unique_articles = []
        seen_titles = set()
        for article in articles:
            if article.title not in seen_titles:
                seen_titles.add(article.title)
                unique_articles.append(article)

        print(f"[ISPE-PE] Successfully collected {len(unique_articles)} articles")
        return unique_articles

    def _fetch_article_details(self, page, article: NewsArticle) -> None:
        """
        개별 기사 상세 정보 수집

        Args:
            page: Playwright page object
            article: NewsArticle to update
        """
        try:
            page.goto(article.link, timeout=30000, wait_until="networkidle")
            content = page.content()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Try to find published date
            date_elem = soup.select_one('.date, .published, time, .article-date')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                article.published = self._parse_date(date_text)

            # Try to find summary/description
            summary_elem = soup.select_one('.summary, .description, .article-intro, meta[name="description"]')
            if summary_elem:
                if summary_elem.name == 'meta':
                    article.summary = summary_elem.get('content', '')[:500]
                else:
                    article.summary = summary_elem.get_text(strip=True)[:500]

            # Rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"[ISPE-PE] Error fetching article details: {e}")

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """날짜 파싱"""
        if not date_text:
            return None

        formats = [
            "%B %d, %Y",      # January 15, 2026
            "%b %d, %Y",      # Jan 15, 2026
            "%Y-%m-%d",       # 2026-01-15
            "%d/%m/%Y",       # 15/01/2026
            "%m/%d/%Y",       # 01/15/2026
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue

        return None


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ISPE PE Magazine Scraper (Login Required)")
    parser.add_argument("--days", type=int, default=30, help="Days back to scrape")
    parser.add_argument("--username", default=None, help="ISPE username")
    parser.add_argument("--password", default=None, help="ISPE password")
    args = parser.parse_args()

    scraper = ISPEPEScraper(username=args.username, password=args.password)

    print("=" * 60)
    print("ISPE Pharmaceutical Engineering Magazine Scraper")
    print("=" * 60)

    articles = scraper.fetch_news(days_back=args.days)

    print(f"\nTotal collected: {len(articles)} articles\n")

    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:60]}...")
        print(f"   URL: {article.link}")
        print()
