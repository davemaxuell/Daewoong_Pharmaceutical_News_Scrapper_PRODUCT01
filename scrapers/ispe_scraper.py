# ISPE (International Society for Pharmaceutical Engineering) Scraper
# ISPE 제약 엔지니어링 스크래퍼 - 주사제/고형제 제조 공정, QA 이슈

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


class ISPEScraper(BaseScraper):
    """
    ISPE (International Society for Pharmaceutical Engineering) 스크래퍼

    수집 소스 (3개만 사용):
    1. https://ispe.org/news - ISPE 뉴스 페이지
    2. https://ispe.org/rss.xml - ISPE RSS 피드
    3. https://www2.smartbrief.com/getLast.action?mode=last&b=ispe - ISPE SmartBrief 뉴스레터

    키워드: keywords.py의 공통 키워드 사용
    """

    BASE_URL = "https://ispe.org"

    @property
    def source_name(self) -> str:
        return "ISPE"

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
            'Accept-Encoding': 'gzip, deflate, br',
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
        ISPE 기사 수집 - 3개 소스만 사용

        Sources:
        1. https://ispe.org/news
        2. https://ispe.org/rss.xml
        3. https://www2.smartbrief.com/getLast.action?mode=last&b=ispe

        Args:
            query: 추가 검색 키워드 (선택)
            days_back: 수집 기간 (None이면 자동 계산)

        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()

        cutoff_date = datetime.now() - timedelta(days=days_back)

        print(f"[ISPE] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")

        articles = []

        # Create session for cookie persistence
        self.session = requests.Session()
        self.session.headers.update(self.get_headers())

        # 1. ISPE News page
        articles.extend(self._scrape_news_page(cutoff_date, query))

        # 2. ISPE RSS feed
        articles.extend(self._scrape_rss_feed(cutoff_date, query))

        # 3. SmartBrief Newsletter
        articles.extend(self._scrape_smartbrief(cutoff_date, query))

        print(f"[ISPE] Total collected: {len(articles)} articles")
        return articles

    def _scrape_rss_feed(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Fetch from ISPE RSS feed at https://ispe.org/rss.xml"""
        articles = []

        try:
            rss_url = f"{self.BASE_URL}/rss.xml"
            print(f"[ISPE RSS] Fetching: {rss_url}")

            time.sleep(2)  # Polite delay
            response = self.session.get(rss_url, timeout=30)

            if response.status_code == 403:
                print(f"[ISPE RSS] 403 Forbidden - blocked")
                return articles
            elif response.status_code == 404:
                print(f"[ISPE RSS] 404 Not Found - RSS feed not available")
                return articles

            response.raise_for_status()

            # Parse as XML
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')

            print(f"[ISPE RSS] Found {len(items)} RSS items")

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

                    # Get summary from RSS
                    summary = desc_elem.get_text(strip=True) if desc_elem else ""

                    # Keyword filter on title and summary first
                    if not self._matches_keywords(title, summary, query):
                        continue

                    # Try to fetch full article content
                    print(f"[ISPE RSS] Fetching article: {title[:60]}...")
                    article = self._parse_article(link, cutoff_date, query,
                                                 rss_title=title, rss_published=published, rss_summary=summary)

                    if article:
                        articles.append(article)
                        print(f"[ISPE RSS] ✓ Added: {title[:60]}...")

                except Exception as e:
                    print(f"[ISPE RSS] Error parsing RSS item: {e}")
                    continue

            print(f"[ISPE RSS] Collected {len(articles)} articles from RSS")

        except Exception as e:
            print(f"[ISPE RSS] Error fetching RSS: {e}")

        return articles

    def _scrape_news_page(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Scrape ISPE News page at https://ispe.org/news"""
        articles = []

        try:
            url = f"{self.BASE_URL}/news"
            print(f"[ISPE News] Fetching: {url}")

            time.sleep(3)  # Polite delay
            response = self.session.get(url, timeout=30)

            if response.status_code == 403:
                print("[ISPE News] 403 Forbidden - ISPE blocks automated access")
                return articles
            elif response.status_code == 404:
                print("[ISPE News] 404 Not Found")
                return articles

            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find news article links
            article_links = []

            # Method 1: article tags
            for article_tag in soup.find_all('article', limit=50):
                link_elem = article_tag.find('a', href=True)
                if link_elem:
                    article_links.append(link_elem['href'])

            # Method 2: news-specific classes
            for link in soup.find_all('a', class_=['news-link', 'article-link', 'post-link', 'card-link'], limit=50):
                if link.get('href'):
                    article_links.append(link['href'])

            # Method 3: href pattern matching (links with /news/ in path)
            for link in soup.find_all('a', href=True, limit=100):
                href = link['href']
                if '/news/' in href and len(href.split('/')) > 3:
                    article_links.append(href)

            # Remove duplicates
            article_links = list(set(article_links))

            print(f"[ISPE News] Found {len(article_links)} article links")

            # Parse each article
            for i, link in enumerate(article_links[:20], 1):  # Max 20
                try:
                    article = self._parse_article(link, cutoff_date, query)
                    if article:
                        articles.append(article)

                    # Rate limiting
                    if i % 5 == 0:
                        time.sleep(1)

                except Exception as e:
                    print(f"[ISPE News] Error parsing article {link}: {e}")
                    continue

        except Exception as e:
            print(f"[ISPE News] Error scraping news page: {e}")

        return articles

    def _scrape_smartbrief(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """Scrape ISPE SmartBrief Newsletter"""
        articles = []

        try:
            url = "https://www2.smartbrief.com/getLast.action?mode=last&b=ispe"
            print(f"[ISPE SmartBrief] Fetching: {url}")

            time.sleep(3)  # Polite delay
            response = self.session.get(url, timeout=30)

            if response.status_code == 403:
                print("[ISPE SmartBrief] 403 Forbidden - blocked")
                return articles
            elif response.status_code == 404:
                print("[ISPE SmartBrief] 404 Not Found")
                return articles

            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # SmartBrief newsletter items (try various selectors)
            news_items = []

            # Method 1: Look for article/story divs
            for item in soup.find_all(['div', 'article'], class_=['story', 'item', 'news-item', 'article-item'], limit=50):
                news_items.append(item)

            # Method 2: Look for links within newsletter content
            if not news_items:
                main_content = soup.find(['div', 'main'], class_=['content', 'newsletter', 'main-content'])
                if main_content:
                    news_items = main_content.find_all('a', href=True, limit=50)

            print(f"[ISPE SmartBrief] Found {len(news_items)} potential items")

            for item in news_items[:30]:  # Max 30 items
                try:
                    # Extract link
                    link_elem = item if item.name == 'a' else item.find('a', href=True)
                    if not link_elem:
                        continue

                    link = link_elem.get('href', '')
                    if not link or not link.startswith('http'):
                        continue

                    # Extract title
                    title = None
                    title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    elif link_elem:
                        title = link_elem.get_text(strip=True)

                    if not title or len(title) < 10:
                        continue

                    # Extract summary/description
                    summary = ""
                    desc_elem = item.find(['p', 'div'], class_=['description', 'summary', 'excerpt'])
                    if desc_elem:
                        summary = desc_elem.get_text(strip=True)
                    elif item.name != 'a':
                        summary = item.get_text(strip=True)[:300]

                    # Extract date if available
                    published = None
                    date_elem = item.find(['time', 'span'], class_=['date', 'publish-date'])
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get_text()
                        published = self._parse_date(date_str)

                    # Skip articles with no date (likely old articles)
                    if not published:
                        print(f"[ISPE] No date found - skipping: {title[:50]}...")
                        continue

                    # Date filter
                    if published < cutoff_date:
                        continue

                    # Keyword filter
                    if not self._matches_keywords(title, summary, query):
                        continue

                    # Classify
                    classifications, matched_keywords = classify_article(title, summary)

                    if not classifications:
                        classifications = ["ISPE", "SmartBrief"]
                        matched_keywords = ["ISPE"]

                    # Add target keywords
                    for keyword in get_all_keywords():
                        if keyword.lower() in f"{title} {summary}".lower():
                            if keyword not in matched_keywords:
                                matched_keywords.append(keyword)

                    article = NewsArticle(
                        title=f"[ISPE SmartBrief] {title}",
                        link=link,
                        published=published,
                        source=self.source_name,
                        summary=summary[:300] if summary else title,
                        full_text=summary[:1000] if summary else title,
                        images=[],
                        scrape_status="success",
                        classifications=classifications,
                        matched_keywords=matched_keywords[:10]
                    )

                    articles.append(article)
                    print(f"[ISPE SmartBrief] ✓ Added: {title[:60]}...")

                except Exception as e:
                    print(f"[ISPE SmartBrief] Error parsing item: {e}")
                    continue

            print(f"[ISPE SmartBrief] Collected {len(articles)} articles")

        except Exception as e:
            print(f"[ISPE SmartBrief] Error scraping SmartBrief: {e}")

        return articles

    def _parse_article(self, link: str, cutoff_date: datetime, query: str = None,
                      rss_title: str = None, rss_published: datetime = None, rss_summary: str = None) -> Optional[NewsArticle]:
        """개별 기사 파싱 (RSS 데이터 우선 사용)"""
        try:
            # Use RSS data if provided
            title = rss_title
            published = rss_published
            summary = rss_summary or ""
            content = summary

            # URL 정규화
            if not link.startswith('http'):
                link = f"{self.BASE_URL}{link}" if link.startswith('/') else f"{self.BASE_URL}/{link}"

            # Try to fetch full article content (if not enough from RSS)
            try:
                time.sleep(1)  # Polite delay
                response = self.session.get(link, timeout=30)

                if response.status_code == 403:
                    # Use RSS data only
                    print(f"[ISPE] 403 Forbidden - using RSS data only")
                else:
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # 제목 추출 (if not from RSS)
                    if not title:
                        for selector in ['h1', 'h1.article-title', 'h1.entry-title', '.page-title']:
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
                            'meta[property="article:published_time"]',
                            '.post-date'
                        ]

                        for selector in date_selectors:
                            date_elem = soup.select_one(selector)
                            if date_elem:
                                date_str = date_elem.get('datetime') or date_elem.get('content') or date_elem.get_text()
                                published = self._parse_date(date_str)
                                if published:
                                    break

                        # URL에서 날짜 추출 시도
                        if not published:
                            parts = link.split('/')
                            for part in parts:
                                if '-2025' in part or '-2026' in part or '-2027' in part:
                                    try:
                                        year = part.split('-')[-1]
                                        published = datetime(int(year), 1, 1)
                                    except:
                                        pass

                    # 본문 추출
                    content_selectors = [
                        'article',
                        '.article-body',
                        '.entry-content',
                        '.post-content',
                        'main'
                    ]

                    for selector in content_selectors:
                        content_elem = soup.select_one(selector)
                        if content_elem:
                            # Remove unwanted elements
                            for tag in content_elem.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                                tag.decompose()
                            fetched_content = content_elem.get_text(separator=' ', strip=True)
                            if len(fetched_content) > len(content):
                                content = fetched_content
                            break

                    # Update summary if we got more content
                    if content and len(content) > len(summary):
                        summary = content[:300] + "..." if len(content) > 300 else content

            except Exception as e:
                # If article fetch fails, use RSS data
                print(f"[ISPE] Could not fetch full article: {e}")
                if not title:
                    return None

            if not title:
                return None

            # 날짜 필터링
            if published and published < cutoff_date:
                return None

            # 키워드 필터링
            if not self._matches_keywords(title, content, query):
                return None

            # 분류
            classifications, matched_keywords = classify_article(title, summary)

            # ISPE 특화 분류 추가
            if not classifications:
                classifications = ["ISPE", "제약엔지니어링"]
                matched_keywords = ["ISPE"]

            # 타겟 키워드 추가
            for keyword in get_all_keywords():
                if keyword.lower() in f"{title} {content}".lower():
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

            return NewsArticle(
                title=f"[ISPE] {title}",
                link=link,
                published=published,
                source=self.source_name,
                summary=summary[:300] if summary else title,
                full_text=content[:1000] if content else summary,
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords[:10]
            )

        except Exception as e:
            print(f"[ISPE] Error parsing article: {e}")
            return None

    def _matches_keywords(self, title: str, content: str, query: str = None) -> bool:
        """키워드 매칭 확인 (keywords.py 공통 키워드 사용)"""
        text = f"{title} {content}".lower()

        # 추가 쿼리 확인
        if query and query.lower() not in text:
            return False

        # 공통 키워드 중 하나라도 있으면 True
        for keyword in get_all_keywords():
            if keyword.lower() in text:
                return True

        return False

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """다양한 날짜 형식 파싱"""
        if not date_str:
            return None

        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d %B %Y",
            "%B %d, %Y",
            "%d %b %Y",
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                # Remove timezone info to make it naive (compatible with cutoff_date)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except:
                continue

        return None


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ISPE Scraper")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 3 days or 7 on Monday)")
    parser.add_argument("--query", type=str, default=None,
                       help="Additional search keyword")
    args = parser.parse_args()

    scraper = ISPEScraper()

    print("=" * 60)
    print("ISPE (International Society for Pharmaceutical Engineering)")
    print("Scraper - 주사제/고형제 제조 공정, QA 이슈")
    print("=" * 60)

    articles = scraper.fetch_news(query=args.query, days_back=args.days)

    print(f"\nTotal collected: {len(articles)} articles\n")

    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:80]}...")
        print(f"   Keywords: {', '.join(article.matched_keywords[:5])}")
        print(f"   {article.link}")
        print()
