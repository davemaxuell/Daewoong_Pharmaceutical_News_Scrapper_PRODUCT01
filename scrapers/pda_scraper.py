# PDA (Parenteral Drug Association) Letter Portal Scraper
# Focuses on Recent News section from https://www.pda.org/pda-letter-portal

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys
import time
import re

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article, get_all_keywords

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    from base_scraper import BaseScraper, NewsArticle


class PDAScraper(BaseScraper):
    """
    PDA (Parenteral Drug Association) Letter Portal 스크래퍼

    수집 소스 (5개):
    1. https://www.pda.org/pda-letter-portal (메인 - Recent Articles)
    2. https://www.pda.org/pda-letter-portal/home/biopharmaceuticals-biotechnology (바이오의약품)
    3. https://www.pda.org/pda-letter-portal/home/aseptic-processing-sterilization (무균공정/멸균)
    4. https://www.pda.org/pda-letter-portal/home/manufacturing-science (제조과학)
    5. https://www.pda.org/pda-letter-portal/home/quality-and-regulatory (품질/규제)

    키워드: keywords.py의 공통 키워드 사용
    """

    BASE_URL = "https://www.pda.org"
    PORTAL_URL = f"{BASE_URL}/pda-letter-portal"

    # 카테고리별 페이지 URLs
    TARGET_CATEGORIES = [
        "/pda-letter-portal/home/biopharmaceuticals-biotechnology",
        "/pda-letter-portal/home/aseptic-processing-sterilization",
        "/pda-letter-portal/home/manufacturing-science",
        "/pda-letter-portal/home/quality-and-regulatory",
    ]

    @property
    def source_name(self) -> str:
        return "PDA Letter"

    @property
    def base_url(self) -> str:
        return self.BASE_URL

    def _get_days_back(self) -> int:
        """
        월요일: 3일 (주말 포함)
        평일: 1일
        """
        import datetime
        today = datetime.datetime.now().weekday()
        if today == 0:  # Monday
            return 3
        return 1

    def get_headers(self) -> dict:
        """Enhanced headers to bypass bot detection"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
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
        PDA Letter Portal에서 Recent News 수집 (5개 소스)

        Args:
            query: 추가 검색 키워드 (선택)
            days_back: 수집 기간 (None이면 자동 설정)

        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)
        print(f"[PDA] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")

        articles = []
        seen_links = set()  # 중복 방지

        # Create session for cookie persistence
        self.session = requests.Session()
        self.session.headers.update(self.get_headers())

        # 1. Scrape main PDA Letter Portal page (Recent Articles)
        print(f"\n[PDA] === Scraping main portal ===")
        portal_articles = self._scrape_portal_page(cutoff_date, query)
        for article in portal_articles:
            if article.link not in seen_links:
                articles.append(article)
                seen_links.add(article.link)

        # 2. Scrape each category page
        for category_path in self.TARGET_CATEGORIES:
            category_name = category_path.split('/')[-1].replace('-', ' ').title()
            print(f"\n[PDA] === Scraping category: {category_name} ===")
            category_articles = self._scrape_category_page(category_path, cutoff_date, query)
            for article in category_articles:
                if article.link not in seen_links:
                    articles.append(article)
                    seen_links.add(article.link)
                    print(f"[PDA {category_name}] + Added: {article.title[:50]}...")

        print(f"\n[PDA] Total collected: {len(articles)} articles from 5 sources")
        return articles

    def _scrape_portal_page(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Scrape PDA Letter Portal main page for Recent Articles"""
        articles = []

        try:
            print(f"[PDA Portal] Fetching: {self.PORTAL_URL}")

            time.sleep(2)  # Polite delay
            response = self.session.get(self.PORTAL_URL, timeout=30)

            if response.status_code == 403:
                print("[PDA Portal] 403 Forbidden - blocked")
                return articles
            elif response.status_code == 404:
                print("[PDA Portal] 404 Not Found")
                return articles

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all article links
            article_links = set()

            # Method 1: Look for links matching the full-article pattern
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/pda-letter-portal/home/full-article/' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        href = f"{self.BASE_URL}{href}"
                    elif not href.startswith('http'):
                        href = f"{self.BASE_URL}/{href}"
                    article_links.add(href)

            print(f"[PDA Portal] Found {len(article_links)} article links")

            # Method 2: Look for Recent Articles section specifically
            # Try to find section with "Recent Articles" or "Past 60 Days"
            for heading in soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'Recent.*Articles', re.I)):
                parent = heading.find_parent(['div', 'section'])
                if parent:
                    for link in parent.find_all('a', href=True):
                        href = link.get('href', '')
                        if '/pda-letter-portal/home/full-article/' in href:
                            if href.startswith('/'):
                                href = f"{self.BASE_URL}{href}"
                            article_links.add(href)

            # Parse each article
            for i, link in enumerate(list(article_links)[:30], 1):  # Max 30 articles
                try:
                    article = self._parse_article(link, cutoff_date, query)
                    if article:
                        articles.append(article)
                        print(f"[PDA Portal] ✓ Added: {article.title[:60]}...")

                    # Rate limiting
                    if i % 5 == 0:
                        time.sleep(1)

                except Exception as e:
                    print(f"[PDA Portal] Error parsing article {link}: {e}")
                    continue

            print(f"[PDA Portal] Collected {len(articles)} articles")

        except Exception as e:
            print(f"[PDA Portal] Error scraping portal page: {e}")

        return articles

    def _scrape_category_page(self, category_path: str, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Scrape a specific PDA Letter category page"""
        articles = []
        category_url = f"{self.BASE_URL}{category_path}"
        category_name = category_path.split('/')[-1].replace('-', ' ').title()

        try:
            print(f"[PDA {category_name}] Fetching: {category_url}")

            time.sleep(2)  # Polite delay
            response = self.session.get(category_url, timeout=30)

            if response.status_code == 403:
                print(f"[PDA {category_name}] 403 Forbidden - blocked")
                return articles
            elif response.status_code == 404:
                print(f"[PDA {category_name}] 404 Not Found")
                return articles

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all article links
            article_links = set()

            # Method 1: Look for links matching the full-article pattern
            for link_elem in soup.find_all('a', href=True):
                href = link_elem.get('href', '')
                if '/pda-letter-portal/home/full-article/' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        href = f"{self.BASE_URL}{href}"
                    elif not href.startswith('http'):
                        href = f"{self.BASE_URL}/{href}"
                    article_links.add(href)

            # Method 2: Look for article cards/items
            for article_item in soup.find_all(['div', 'article'], class_=re.compile(r'(article|item|card|entry)', re.I)):
                for link_elem in article_item.find_all('a', href=True):
                    href = link_elem.get('href', '')
                    if '/pda-letter-portal/' in href and 'full-article' in href:
                        if href.startswith('/'):
                            href = f"{self.BASE_URL}{href}"
                        article_links.add(href)

            print(f"[PDA {category_name}] Found {len(article_links)} article links")

            # Parse each article
            for i, link in enumerate(list(article_links)[:20], 1):  # Max 20 articles per category
                try:
                    article = self._parse_article(link, cutoff_date, query, category_name)
                    if article:
                        articles.append(article)

                    # Rate limiting
                    if i % 5 == 0:
                        time.sleep(1)

                except Exception as e:
                    print(f"[PDA {category_name}] Error parsing article {link}: {e}")
                    continue

            print(f"[PDA {category_name}] Collected {len(articles)} articles")

        except Exception as e:
            print(f"[PDA {category_name}] Error scraping category page: {e}")

        return articles

    def _parse_article(self, link: str, cutoff_date: datetime, query: str = None, category: str = None) -> Optional[NewsArticle]:
        """
        개별 기사 파싱

        Args:
            link: 기사 URL
            cutoff_date: 수집 기준일
            query: 추가 검색 키워드
            category: 카테고리 이름 (예: "Biopharmaceuticals Biotechnology")
        """
        try:
            # URL 정규화
            if not link.startswith('http'):
                link = f"{self.BASE_URL}{link}" if link.startswith('/') else f"{self.BASE_URL}/{link}"

            # Fetch article page
            time.sleep(1)  # Polite delay
            response = self.session.get(link, timeout=30)

            if response.status_code == 403:
                print(f"[PDA] 403 Forbidden - skipping")
                return None

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = None
            for selector in ['h1', 'h1.title', 'h1.article-title', 'h1.entry-title', '.page-title', 'article h1']:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            if not title:
                print(f"[PDA] No title found for {link}")
                return None

            # Extract date
            published = None
            date_selectors = [
                'time[datetime]',
                '.publish-date',
                '.article-date',
                '.post-date',
                'meta[property="article:published_time"]',
                'meta[name="publishdate"]',
                '.date',
                'span.date'
            ]

            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = date_elem.get('datetime') or date_elem.get('content') or date_elem.get_text()
                    published = self._parse_date(date_str)
                    if published:
                        break

            # Try to find date in article text (PDA format: "30 January 2026")
            if not published:
                text_content = soup.get_text()
                date_pattern = r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})'
                match = re.search(date_pattern, text_content)
                if match:
                    published = self._parse_date(match.group(1))

            # Skip articles with no date (likely old articles)
            if not published:
                print(f"[PDA] No date found - skipping: {title[:50]}...")
                return None

            # Date filter
            if published < cutoff_date:
                return None

            # Extract author
            author = None
            for selector in ['.author', '.byline', 'meta[name="author"]', 'span.author']:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.get('content') or author_elem.get_text(strip=True)
                    break

            # Extract content
            content = ""
            summary = ""

            content_selectors = [
                'article',
                '.article-body',
                '.article-content',
                '.entry-content',
                '.post-content',
                '.content',
                'main',
                '.main-content'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove unwanted elements
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'footer', 'aside', 'header', 'button', 'form']):
                        tag.decompose()

                    content = content_elem.get_text(separator=' ', strip=True)
                    if len(content) > 200:  # Minimum content length
                        break

            # If no content found, use meta description
            if not content:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    content = meta_desc.get('content', '')

            # Create summary
            if content:
                summary = content[:300] + "..." if len(content) > 300 else content
            else:
                summary = title

            # Keyword filtering
            if not self._matches_keywords(title, content, query):
                return None

            # Classify
            classifications, matched_keywords = classify_article(title, summary)

            # PDA 특화 분류 추가
            if not classifications:
                classifications = ["PDA", "Parenteral"]

            # Add category to classifications
            if category:
                category_tag = category.replace(" ", "-")
                if category_tag not in classifications:
                    classifications.append(category_tag)

            # Add target keywords
            for keyword in get_all_keywords():
                if keyword.lower() in f"{title} {content}".lower():
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

            # Build title with main source name only (no category/author suffix)
            title_prefix = "[PDA Letter]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=link,
                published=published,
                source=self.source_name,
                summary=summary[:300] if summary else title,
                full_text=content[:10000] if content else summary,  # Increased to 10000 chars for AI summarization
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords[:10]
            )

        except Exception as e:
            print(f"[PDA] Error parsing article: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """다양한 날짜 형식 파싱"""
        if not date_str:
            return None

        # Clean up date string
        date_str = date_str.strip()

        # Common date formats (PDA uses formats like "30 January 2026")
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO with timezone
            "%Y-%m-%dT%H:%M:%S",    # ISO without timezone
            "%Y-%m-%d",             # ISO date
            "%d %B %Y",             # 30 January 2026
            "%B %d, %Y",            # January 30, 2026
            "%d %b %Y",             # 30 Jan 2026
            "%b %d, %Y",            # Jan 30, 2026
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 (RSS)
            "%a, %d %b %Y %H:%M:%S",     # RFC 2822 without timezone
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Remove timezone info if present
                if parsed_date.tzinfo:
                    parsed_date = parsed_date.replace(tzinfo=None)
                return parsed_date
            except ValueError:
                continue

        # Try dateutil as fallback
        try:
            from dateutil import parser
            return parser.parse(date_str).replace(tzinfo=None)
        except:
            pass

        return None

    def _matches_keywords(self, title: str, content: str, query: str = None) -> bool:
        """키워드 매칭 확인"""
        text = f"{title} {content}".lower()

        # Check target keywords
        for keyword in get_all_keywords():
            if keyword.lower() in text:
                # Additional query check
                if query:
                    if query.lower() in text:
                        return True
                else:
                    return True

        # If query provided but no target keyword match
        if query and query.lower() in text:
            return True

        return False


def main():
    """테스트 실행"""
    import argparse

    parser = argparse.ArgumentParser(description='PDA Letter Portal Scraper')
    parser.add_argument('--days', type=int, default=30, help='Days back to scrape (default: 30)')
    args = parser.parse_args()

    scraper = PDAScraper()
    articles = scraper.fetch_news(days_back=args.days)

    print(f"\nTotal collected: {len(articles)} articles\n")

    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:80]}...")
        print(f"   Keywords: {', '.join(article.matched_keywords[:5])}")
        print(f"   {article.link}")
        print()


if __name__ == "__main__":
    main()
