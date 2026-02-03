# Pharmaceutical Online Scraper
# Focuses on finished pharmaceutical manufacturing plant operations
# https://www.pharmaceuticalonline.com/

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


class PharmaceuticalOnlineScraper(BaseScraper):
    """
    Pharmaceutical Online 스크래퍼

    수집 소스 (10개):
    1. https://www.pharmaceuticalonline.com/solution/critical-environments (클린룸/제조환경)
    2. https://www.pharmaceuticalonline.com/solution/solid-dose-manufacturing (고형제 제조)
    3. https://www.pharmaceuticalonline.com/solution/liquid-dose-manufacturing (액제 제조)
    4. https://www.pharmaceuticalonline.com/solution/inspection (검사)
    5. https://www.pharmaceuticalonline.com/solution/serialization (시리얼화)
    6. https://www.pharmaceuticalonline.com/solution/packaging (포장)
    7. https://www.pharmaceuticalonline.com/solution/regulatory-compliance (규제 준수)
    8. https://www.pharmaceuticalonline.com/solution/quality-assurance (QA)
    9. https://www.pharmaceuticalonline.com/solution/quality-control (QC)
    10. https://www.pharmaceuticalonline.com/solution/production (생산)

    키워드: keywords.py의 공통 키워드 사용
    """

    BASE_URL = "https://www.pharmaceuticalonline.com"

    # 타겟 카테고리 (완제의약품 공장 실무 관련) - 10개
    TARGET_CATEGORIES = [
        # Production categories
        "/solution/critical-environments",
        "/solution/solid-dose-manufacturing",
        "/solution/liquid-dose-manufacturing",
        "/solution/production",

        # Inspection & Packaging
        "/solution/inspection",
        "/solution/serialization",
        "/solution/packaging",

        # Quality categories
        "/solution/regulatory-compliance",
        "/solution/quality-assurance",
        "/solution/quality-control",
    ]

    @property
    def source_name(self) -> str:
        return "Pharmaceutical Online"

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
            'Accept-Language': 'en-US,en;q=0.9',
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
        Pharmaceutical Online에서 제조 관련 뉴스 수집

        Args:
            query: 추가 검색 키워드 (선택)
            days_back: 수집 기간 (None이면 자동)

        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)
        print(f"[Pharmaceutical Online] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")

        articles = []

        # Create session for cookie persistence
        self.session = requests.Session()
        self.session.headers.update(self.get_headers())

        # Scrape each target category
        for category in self.TARGET_CATEGORIES:
            category_articles = self._scrape_category(category, cutoff_date, query)
            articles.extend(category_articles)
            time.sleep(2)  # Rate limiting between categories

        # Remove duplicates by link
        seen_links = set()
        unique_articles = []
        for article in articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)

        print(f"[Pharmaceutical Online] Total collected: {len(unique_articles)} articles")
        return unique_articles

    def _scrape_category(self, category_path: str, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """카테고리 페이지에서 기사 수집"""
        articles = []

        try:
            url = f"{self.BASE_URL}{category_path}"
            print(f"[Pharmaceutical Online] Fetching category: {url}")

            time.sleep(1)  # Polite delay
            response = self.session.get(url, timeout=30)

            if response.status_code == 403:
                print(f"[Pharmaceutical Online] 403 Forbidden - blocked")
                return articles
            elif response.status_code == 404:
                print(f"[Pharmaceutical Online] 404 Not Found")
                return articles

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article cards/links
            article_links = set()

            # Method 1: Look for links with /doc/ pattern
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/doc/' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        href = f"{self.BASE_URL}{href}"
                    elif not href.startswith('http'):
                        href = f"{self.BASE_URL}/{href}"
                    article_links.add(href)

            # Method 2: Look for article cards with specific classes
            for card in soup.find_all(['div', 'article'], class_=re.compile(r'card|article|item', re.I)):
                link_elem = card.find('a', href=True)
                if link_elem:
                    href = link_elem.get('href', '')
                    if '/doc/' in href:
                        if href.startswith('/'):
                            href = f"{self.BASE_URL}{href}"
                        article_links.add(href)

            print(f"[Pharmaceutical Online] Found {len(article_links)} article links in category")

            # Parse each article (limit to 20 per category)
            for i, link in enumerate(list(article_links)[:20], 1):
                try:
                    article = self._parse_article(link, cutoff_date, query)
                    if article:
                        articles.append(article)
                        print(f"[Pharmaceutical Online] ✓ Added: {article.title[:60]}...")

                    # Rate limiting
                    if i % 5 == 0:
                        time.sleep(1)

                except Exception as e:
                    print(f"[Pharmaceutical Online] Error parsing article {link}: {e}")
                    continue

            print(f"[Pharmaceutical Online] Category collected: {len(articles)} articles")

        except Exception as e:
            print(f"[Pharmaceutical Online] Error scraping category {category_path}: {e}")

        return articles

    def _parse_article(self, link: str, cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """개별 기사 파싱"""
        try:
            # URL 정규화
            if not link.startswith('http'):
                link = f"{self.BASE_URL}{link}" if link.startswith('/') else f"{self.BASE_URL}/{link}"

            # Fetch article page
            time.sleep(1)  # Polite delay
            response = self.session.get(link, timeout=30)

            if response.status_code == 403:
                print(f"[Pharmaceutical Online] 403 Forbidden - skipping")
                return None

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = None
            for selector in ['h1', 'h1.title', 'h1.article-title', '.article-title', '.page-title']:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            if not title:
                print(f"[Pharmaceutical Online] No title found for {link}")
                return None

            # Extract date
            published = None
            date_selectors = [
                'time[datetime]',
                '.publish-date',
                '.article-date',
                '.date',
                'meta[property="article:published_time"]',
                'meta[name="publishdate"]'
            ]

            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = date_elem.get('datetime') or date_elem.get('content') or date_elem.get_text()
                    published = self._parse_date(date_str)
                    if published:
                        break

            # Try to find date in text (MM/DD/YYYY format common on this site)
            if not published:
                text_content = soup.get_text()
                date_pattern = r'(\d{1,2}/\d{1,2}/\d{4})'
                match = re.search(date_pattern, text_content)
                if match:
                    published = self._parse_date(match.group(1))

            # Use current date if no date found
            if not published:
                published = datetime.now()

            # Date filter
            if published < cutoff_date:
                return None

            # Extract author/source
            author = None
            for selector in ['.author', '.byline', 'meta[name="author"]']:
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
                '.content',
                'main',
                '.main-content'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove unwanted elements
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                        tag.decompose()

                    content = content_elem.get_text(separator=' ', strip=True)
                    if len(content) > 200:
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

            # Add site-specific classification
            if not classifications:
                classifications = ["Pharmaceutical Manufacturing"]

            # Add target keywords
            for keyword in get_all_keywords():
                if keyword.lower() in f"{title} {content}".lower():
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

            # Add author to title if available
            title_prefix = "[Pharmaceutical Online]"
            if author:
                title_prefix = f"[Pharmaceutical Online - {author}]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=link,
                published=published,
                source=self.source_name,
                summary=summary[:300] if summary else title,
                full_text=content[:10000] if content else summary,  # 10000 chars for AI summarization
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords[:10]
            )

        except Exception as e:
            print(f"[Pharmaceutical Online] Error parsing article: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """다양한 날짜 형식 파싱"""
        if not date_str:
            return None

        # Clean up date string
        date_str = date_str.strip()

        # Common date formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO with timezone
            "%Y-%m-%dT%H:%M:%S",    # ISO without timezone
            "%Y-%m-%d",             # ISO date
            "%m/%d/%Y",             # MM/DD/YYYY (common on this site)
            "%d/%m/%Y",             # DD/MM/YYYY
            "%B %d, %Y",            # January 30, 2026
            "%d %B %Y",             # 30 January 2026
            "%b %d, %Y",            # Jan 30, 2026
            "%d %b %Y",             # 30 Jan 2026
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

    parser = argparse.ArgumentParser(description='Pharmaceutical Online Scraper')
    parser.add_argument('--days', type=int, default=None, help='Days back to scrape (default: auto)')
    args = parser.parse_args()

    scraper = PharmaceuticalOnlineScraper()
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
