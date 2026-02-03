# BioProcess International Scraper
# BioProcess International QA/QC 스크래퍼 - 바이오의약품 품질관리, 분석법

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys
import time
import warnings

# Suppress XML parsing warnings for RSS feeds
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article, get_all_keywords

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    from base_scraper import BaseScraper, NewsArticle


class BioProcessScraper(BaseScraper):
    """
    BioProcess International 스크래퍼

    수집 소스 (4개):
    1. https://www.bioprocessintl.com/ (메인 - RSS feed)
    2. https://www.bioprocessintl.com/manufacturing/validation (제조 검증)
    3. https://www.bioprocessintl.com/manufacturing/fill-finish (충전/마감)
    4. https://www.bioprocessintl.com/analytical/qa-qc (QA/QC 분석)

    키워드: keywords.py의 공통 키워드 사용
    """

    BASE_URL = "https://www.bioprocessintl.com"

    # 타겟 카테고리 URLs
    TARGET_CATEGORIES = [
        "/manufacturing/validation",
        "/manufacturing/fill-finish",
        "/analytical/qa-qc",
    ]

    @property
    def source_name(self) -> str:
        return "BioProcess International"

    @property
    def base_url(self) -> str:
        return self.BASE_URL

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

    def get_headers(self) -> dict:
        """Enhanced headers to bypass bot detection"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Accept-Encoding': 'gzip, deflate',  # Removed 'br' - brotli not supported by requests without extra package
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        BioProcess International 기사 수집 (4개 소스)

        Args:
            query: 추가 검색 키워드 (선택)
            days_back: 수집 기간 (None이면 자동 계산)

        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)

        print(f"[BioProcess] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")

        articles = []
        seen_links = set()  # 중복 방지

        # Create session for cookie persistence
        self.session = requests.Session()
        self.session.headers.update(self.get_headers())

        # 1. RSS feed (primary source - reliable and complete)
        print(f"\n[BioProcess] === Scraping RSS Feed ===")
        rss_articles = self._scrape_rss_feed(cutoff_date, query)
        for article in rss_articles:
            if article.link not in seen_links:
                articles.append(article)
                seen_links.add(article.link)

        # 2. Scrape each target category
        for category_path in self.TARGET_CATEGORIES:
            category_name = category_path.split('/')[-1].replace('-', ' ').title()
            print(f"\n[BioProcess] === Scraping category: {category_name} ===")
            category_articles = self._scrape_category_page(category_path, cutoff_date, query)
            for article in category_articles:
                if article.link not in seen_links:
                    articles.append(article)
                    seen_links.add(article.link)
                    print(f"[BioProcess {category_name}] + Added: {article.title[:50]}...")

        print(f"\n[BioProcess] Total collected: {len(articles)} articles from 4 sources")
        return articles

    def _scrape_category_page(self, category_path: str, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Generic category page scraping method"""
        articles = []
        category_url = f"{self.BASE_URL}{category_path}"
        category_name = category_path.split('/')[-1].replace('-', ' ').title()

        try:
            print(f"[BioProcess {category_name}] Fetching: {category_url}")

            time.sleep(2)  # Polite delay
            response = self.session.get(category_url, timeout=30)

            if response.status_code == 403:
                print(f"[BioProcess {category_name}] 403 Forbidden - site blocks automated access")
                return articles
            elif response.status_code == 404:
                print(f"[BioProcess {category_name}] 404 Not Found")
                return articles

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links
            article_links = []

            # Method 1: Find article cards/containers
            for article_card in soup.find_all(['article', 'div'], class_=['article', 'post', 'card', 'item'], limit=50):
                link_elem = article_card.find('a', href=True)
                if link_elem:
                    href = link_elem['href']
                    # Filter relevant article links (exclude nav, tags, authors, etc.)
                    if any(x in href for x in ['/article/', '/news/', '/feature/', '/analytical/', '/manufacturing/']):
                        article_links.append(href)

            # Method 2: Find headings with links
            for heading in soup.find_all(['h2', 'h3', 'h4'], limit=50):
                link_elem = heading.find('a', href=True)
                if link_elem:
                    href = link_elem['href']
                    if any(x in href for x in ['/article/', '/news/', '/feature/', '/analytical/', '/manufacturing/']):
                        article_links.append(href)

            # Method 3: Find all links with article patterns
            for link in soup.find_all('a', href=True, limit=100):
                href = link['href']
                # Filter for article URLs (not navigation, tags, authors, etc.)
                if '/analytical/' in href or '/manufacturing/' in href:
                    # Make sure it's an article, not a category page
                    parts = href.split('/')
                    if len(parts) > 4:  # /analytical/qa-qc/article-title format
                        article_links.append(href)

            # Remove duplicates while preserving order
            seen = set()
            article_links = [x for x in article_links if not (x in seen or seen.add(x))]

            print(f"[BioProcess {category_name}] Found {len(article_links)} article links")

            # Parse each article
            for i, link in enumerate(article_links[:20], 1):  # Limit to 20 articles per category
                try:
                    article = self._parse_article(link, cutoff_date, query, category=category_name)
                    if article:
                        articles.append(article)

                    # Rate limiting
                    if i % 5 == 0:
                        time.sleep(2)

                except Exception as e:
                    print(f"[BioProcess {category_name}] Error parsing article {link}: {e}")
                    continue

            print(f"[BioProcess {category_name}] Collected {len(articles)} articles")

        except Exception as e:
            print(f"[BioProcess {category_name}] Error scraping category page: {e}")

        return articles

    def _scrape_rss_feed(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Fetch from BioProcess International RSS feed"""
        articles = []

        try:
            rss_url = f"{self.BASE_URL}/rss.xml"
            print(f"[BioProcess RSS] Fetching: {rss_url}")

            time.sleep(2)  # Polite delay
            response = self.session.get(rss_url, timeout=30)
            response.raise_for_status()

            # Parse as XML
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')

            print(f"[BioProcess RSS] Found {len(items)} RSS items")

            for item in items:
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    date_elem = item.find('pubDate')
                    desc_elem = item.find('description')

                    if not title_elem or not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = link_elem.get_text(strip=True)

                    # Parse date
                    published = None
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        published = self._parse_date(date_str)

                    # Date filter
                    if published and published < cutoff_date:
                        continue

                    # Get summary from RSS description
                    summary = desc_elem.get_text(strip=True) if desc_elem else ""

                    # Keyword filter on title and summary first (lightweight)
                    if not self._matches_keywords(title, summary, query):
                        continue

                    # Fetch full article content
                    print(f"[BioProcess RSS] Fetching article: {title[:60]}...")
                    article = self._parse_article(link, cutoff_date, query, rss_title=title, rss_published=published, rss_summary=summary)

                    if article:
                        articles.append(article)
                        print(f"[BioProcess RSS] ✓ Added: {title[:60]}...")

                except Exception as e:
                    print(f"[BioProcess RSS] Error parsing RSS item: {e}")
                    continue

            print(f"[BioProcess RSS] Collected {len(articles)} articles")

        except Exception as e:
            print(f"[BioProcess RSS] Error fetching RSS: {e}")

        return articles

    def _parse_article(self, link: str, cutoff_date: datetime, query: str = None,
                      rss_title: str = None, rss_published: datetime = None, rss_summary: str = None,
                      category: str = None) -> Optional[NewsArticle]:
        """
        개별 기사 파싱

        Args:
            link: 기사 URL
            cutoff_date: 수집 기준일
            query: 추가 검색 키워드
            rss_title: RSS에서 가져온 제목
            rss_published: RSS에서 가져온 발행일
            rss_summary: RSS에서 가져온 요약
            category: 카테고리 이름 (예: "Validation", "Fill Finish", "Qa Qc")
        """
        try:
            # Use RSS data if provided
            title = rss_title
            published = rss_published
            summary = rss_summary
            content = summary or ""

            # URL 정규화
            if not link.startswith('http'):
                link = f"{self.BASE_URL}{link}" if link.startswith('/') else f"{self.BASE_URL}/{link}"

            # Try to fetch full article content
            try:
                time.sleep(1)  # Polite delay
                response = self.session.get(link, timeout=30)

                if response.status_code == 403:
                    # Use RSS data only
                    print(f"[BioProcess] 403 Forbidden - using RSS data only")
                else:
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # 제목 추출 (if not from RSS)
                    if not title:
                        for selector in ['h1', 'h1.title', 'h1.article-title', 'h1.entry-title', '.page-title', 'article h1']:
                            title_elem = soup.select_one(selector)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                break

                    # 날짜 추출 (if not from RSS)
                    if not published:
                        date_selectors = [
                            'time[datetime]',
                            '.publish-date',
                            '.article-date',
                            '.post-date',
                            'meta[property="article:published_time"]',
                            'meta[name="publishdate"]',
                        ]

                        for selector in date_selectors:
                            date_elem = soup.select_one(selector)
                            if date_elem:
                                date_str = date_elem.get('datetime') or date_elem.get('content') or date_elem.get_text()
                                published = self._parse_date(date_str)
                                if published:
                                    break

                    # 본문 추출
                    content_selectors = [
                        'article',
                        '.article-body',
                        '.article-content',
                        '.entry-content',
                        '.post-content',
                        '.content',
                        'main'
                    ]

                    for selector in content_selectors:
                        content_elem = soup.select_one(selector)
                        if content_elem:
                            # Remove unwanted elements
                            for tag in content_elem.find_all(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                                tag.decompose()
                            fetched_content = content_elem.get_text(separator=' ', strip=True)
                            if len(fetched_content) > len(content):
                                content = fetched_content
                            break

                    # Update summary if we got more content
                    if content and len(content) > len(summary or ""):
                        summary = content[:300] + "..." if len(content) > 300 else content

            except Exception as e:
                # If article fetch fails, use RSS data
                print(f"[BioProcess] Could not fetch full article: {e}")
                if not title:
                    return None

            if not title:
                return None

            # Date filter
            if published and published < cutoff_date:
                return None

            # 키워드 필터링
            if not self._matches_keywords(title, content, query):
                return None

            # 분류
            classifications, matched_keywords = classify_article(title, summary)

            # BioProcess 특화 분류 추가
            if not classifications:
                classifications = ["BioProcess", "바이오의약품"]
                matched_keywords = ["BioProcess"]

            # Add category to classifications
            if category:
                category_tag = category.replace(" ", "-")
                if category_tag not in classifications:
                    classifications.append(category_tag)

            # 타겟 키워드 추가
            for keyword in get_all_keywords():
                if keyword.lower() in f"{title} {content}".lower():
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

            # Build title with category prefix
            title_prefix = "[BioProcess]"
            if category:
                title_prefix = f"[BioProcess - {category}]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=link,
                published=published,
                source=self.source_name,
                summary=summary,
                full_text=content[:10000] if content else summary,  # 10000자로 증가 (AI 요약용)
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords[:10]  # 최대 10개
            )

        except Exception as e:
            print(f"[BioProcess] Error parsing article: {e}")
            return None

    def _matches_keywords(self, title: str, content: str, query: str = None) -> bool:
        """키워드 매칭 확인"""
        text = f"{title} {content}".lower()

        # 추가 쿼리 확인
        if query and query.lower() not in text:
            return False

        # 타겟 키워드 중 하나라도 있으면 True
        for keyword in get_all_keywords():
            if keyword.lower() in text:
                return True

        return False

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """다양한 날짜 형식 파싱"""
        if not date_str:
            return None

        # Clean up common date string issues
        date_str = date_str.strip()

        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d %B %Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %b %Y",
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S %Z",
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Remove timezone info to make it naive
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except:
                continue

        return None


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BioProcess International Scraper")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 3 days or 7 on Monday)")
    parser.add_argument("--query", type=str, default=None,
                       help="Additional search keyword")
    args = parser.parse_args()

    scraper = BioProcessScraper()

    print("=" * 60)
    print("BioProcess International Scraper")
    print("QA/QC & Analytical - 바이오의약품 품질관리, 분석법")
    print("=" * 60)

    articles = scraper.fetch_news(query=args.query, days_back=args.days)

    print(f"\nTotal collected: {len(articles)} articles\n")

    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:80]}...")
        print(f"   Keywords: {', '.join(article.matched_keywords[:5])}")
        print(f"   {article.link}")
        print()
