# Pharmaceutical Online Scraper
# Uses hub pages with date-based filtering for reliable article detection
# https://www.pharmaceuticalonline.com/
#
# Previous approach (rotating category pages) caused false positives because
# the site randomly rotates content on each page load. The hub pages provide
# stable, chronological article listings WITH publication dates.

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional, Set, Dict
import os
import sys
import time
import re
import json

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article, get_all_keywords

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    from base_scraper import BaseScraper, NewsArticle

# Snapshot directory
SNAPSHOT_DIR = os.path.join(PROJECT_ROOT, "snapshots", "pharmaceutical_online")


class PharmaceuticalOnlineScraper(BaseScraper):
    """
    Pharmaceutical Online 스크래퍼 (허브 페이지 기반 + 날짜 필터링)

    작동 방식:
    1. 허브 페이지에서 기사 목록을 날짜와 함께 수집
    2. 날짜 기반 필터링 (최근 N일 이내 기사만)
    3. 이전 스냅샷과 비교하여 새 기사만 식별
    4. 새 기사만 상세 정보 수집
    5. 스냅샷 업데이트

    수집 소스 (2개 허브 페이지):
    1. /hub/bucket/industry-news (업계 뉴스 - FDA, M&A, 시장 보고서)
    2. /hub/bucket/pharma-contributing-editors (편집 기사 - GMP, CDMO, AI, 밸리데이션)

    키워드: keywords.py의 공통 키워드 사용
    """

    BASE_URL = "https://www.pharmaceuticalonline.com"

    # Stable hub pages with chronological listings and dates
    HUB_PAGES = [
        "/hub/bucket/industry-news",
        "/hub/bucket/pharma-contributing-editors",
    ]

    # Maximum number of hub pages to paginate through
    MAX_HUB_PAGINATION = 3

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
        today = datetime.now().weekday()
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
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }

    def _load_snapshot(self) -> Set[str]:
        """Load previous article links snapshot"""
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        snapshot_file = os.path.join(SNAPSHOT_DIR, "article_links.json")

        if os.path.exists(snapshot_file):
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("links", []))
            except Exception as e:
                print(f"[Pharmaceutical Online] Error loading snapshot: {e}")
        return set()

    def _save_snapshot(self, current_links: Set[str], previous_links: Set[str] = None):
        """Save cumulative article links snapshot.
        
        The snapshot stores ALL links ever seen (union of current + previous).
        This prevents articles from being falsely reported as 'new'.
        """
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        snapshot_file = os.path.join(SNAPSHOT_DIR, "article_links.json")

        # Cumulative: merge current links with all previously seen links
        if previous_links:
            all_seen_links = current_links | previous_links
        else:
            all_seen_links = current_links

        data = {
            "updated": datetime.now().isoformat(),
            "count": len(all_seen_links),
            "links": list(all_seen_links)
        }

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[Pharmaceutical Online] Snapshot updated: {len(all_seen_links)} total links (cumulative)")

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from hub page (e.g., '1/29/2026', '12/4/2025')"""
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y")
        except ValueError:
            try:
                return datetime.strptime(date_str.strip(), "%m/%d/%y")
            except ValueError:
                print(f"[Pharmaceutical Online] Could not parse date: '{date_str}'")
                return None

    def _collect_hub_articles(self, days_back: int = None) -> Dict[str, datetime]:
        """Collect article links and dates from hub pages.
        
        Returns:
            Dict mapping article URL -> publication date
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        articles = {}  # url -> date

        session = requests.Session()
        session.headers.update(self.get_headers())

        for hub_path in self.HUB_PAGES:
            # Paginate through hub pages
            for page_num in range(1, self.MAX_HUB_PAGINATION + 1):
                try:
                    if page_num == 1:
                        url = f"{self.BASE_URL}{hub_path}"
                    else:
                        url = f"{self.BASE_URL}{hub_path}?page={page_num}"

                    print(f"[Pharmaceutical Online] Scanning hub: {url}")
                    time.sleep(1)
                    response = session.get(url, timeout=30)

                    if response.status_code != 200:
                        print(f"[Pharmaceutical Online] HTTP {response.status_code} for {url}")
                        break

                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Parse article listings from hub page
                    # Structure: <li class="mb-2 vm-summary-link">
                    #              <a class="d-block" href="/doc/...">Title</a>
                    #              <em class="vm-hub-date">1/29/2026</em>
                    #              <div class="pt-1"><p>Summary</p></div>
                    #            </li>
                    items = soup.select('li.vm-summary-link')
                    
                    if not items:
                        print(f"[Pharmaceutical Online] No articles found on page {page_num}")
                        break
                    
                    found_old = False
                    page_count = 0
                    
                    for item in items:
                        # Extract link
                        link_elem = item.select_one('a[href*="/doc/"]')
                        if not link_elem:
                            continue
                        
                        href = link_elem.get('href', '')
                        if href.startswith('/'):
                            href = f"{self.BASE_URL}{href}"
                        
                        # Extract date
                        date_elem = item.select_one('em.vm-hub-date')
                        if date_elem:
                            pub_date = self._parse_date(date_elem.get_text(strip=True))
                        else:
                            pub_date = None
                        
                        # Date-based filtering
                        if pub_date and pub_date < cutoff_date:
                            found_old = True
                            continue
                        
                        if 'pharmaceuticalonline.com' in href:
                            articles[href] = pub_date or datetime.now()
                            page_count += 1
                    
                    print(f"[Pharmaceutical Online]   Found {page_count} recent articles on page {page_num}")
                    
                    # If we found old articles, no need to check further pages
                    if found_old:
                        print(f"[Pharmaceutical Online]   Reached articles older than {days_back} day(s), stopping pagination")
                        break
                    
                    # Check if there's a next page
                    next_link = soup.select_one(f'a[href*="page={page_num + 1}"]')
                    if not next_link:
                        break
                    
                    time.sleep(1)

                except Exception as e:
                    print(f"[Pharmaceutical Online] Error scanning hub {hub_path} page {page_num}: {e}")
                    break

        print(f"[Pharmaceutical Online] Total recent articles found: {len(articles)}")
        return articles

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        Pharmaceutical Online에서 새 기사 수집 (허브 페이지 + 날짜 기반)

        Args:
            query: 추가 검색 키워드 (선택)
            days_back: 며칠 이내 기사만 수집 (기본: 평일 1일, 월요일 3일)

        Returns:
            NewsArticle 리스트 (새 기사만)
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        print(f"[Pharmaceutical Online] Starting hub-based scrape (last {days_back} day(s))...")

        # Load previous snapshot
        previous_links = self._load_snapshot()
        is_first_run = len(previous_links) == 0

        if is_first_run:
            print(f"[Pharmaceutical Online] First run - creating baseline snapshot")
        else:
            print(f"[Pharmaceutical Online] Previous snapshot: {len(previous_links)} links")

        # Collect recent articles from hub pages (with dates)
        recent_articles = self._collect_hub_articles(days_back)
        current_links = set(recent_articles.keys())

        # Find new links (not in previous snapshot)
        new_links = current_links - previous_links

        if is_first_run:
            # First run: save baseline and return empty (no "new" articles yet)
            self._save_snapshot(current_links)
            print(f"[Pharmaceutical Online] Baseline created with {len(current_links)} links")
            print(f"[Pharmaceutical Online] Run again to detect new articles")
            return []

        if not new_links:
            print(f"[Pharmaceutical Online] No new articles found")
            self._save_snapshot(current_links, previous_links)
            return []

        print(f"[Pharmaceutical Online] Found {len(new_links)} NEW articles!")

        # Fetch details for new articles only
        articles = []
        session = requests.Session()
        session.headers.update(self.get_headers())

        for i, link in enumerate(new_links, 1):
            try:
                pub_date = recent_articles.get(link, datetime.now())
                print(f"[Pharmaceutical Online] [{i}/{len(new_links)}] Fetching: {link[:60]}...")
                article = self._parse_article(session, link, query, pub_date)
                if article:
                    articles.append(article)
                    print(f"[Pharmaceutical Online] ✓ Added: {article.title[:50]}...")

                # Rate limiting
                time.sleep(1)
                if i % 5 == 0:
                    time.sleep(2)

            except Exception as e:
                print(f"[Pharmaceutical Online] Error parsing {link}: {e}")
                continue

        # Save cumulative snapshot
        self._save_snapshot(current_links, previous_links)

        print(f"[Pharmaceutical Online] Total collected: {len(articles)} new articles")
        return articles

    def _parse_article(self, session: requests.Session, link: str, query: str = None, pub_date: datetime = None) -> Optional[NewsArticle]:
        """개별 기사 파싱"""
        try:
            response = session.get(link, timeout=30)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = None
            for selector in ['h1', 'h1.title', 'h1.article-title', '.article-title', '.page-title']:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            if not title:
                return None

            # Extract content
            content = ""
            content_selectors = [
                'article',
                '.article-body',
                '.article-content',
                '.entry-content',
                '.content',
                'main'
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
            summary = content[:300] + "..." if len(content) > 300 else content if content else title

            # Keyword filtering
            if not self._matches_keywords(title, content, query):
                return None

            # Classify
            classifications, matched_keywords = classify_article(title, summary)

            # Add site-specific classification if none
            if not classifications:
                classifications = ["Pharmaceutical Manufacturing"]

            # Add matched target keywords
            for keyword in get_all_keywords():
                if keyword.lower() in f"{title} {content}".lower():
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

            # Build title with main source name only (no author suffix)
            title_prefix = "[Pharmaceutical Online]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=link,
                published=pub_date or datetime.now(),
                source=self.source_name,
                summary=summary[:300] if summary else title,
                full_text=content[:10000] if content else summary,
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords[:10]
            )

        except Exception as e:
            print(f"[Pharmaceutical Online] Error parsing article: {e}")
            return None

    def _matches_keywords(self, title: str, content: str, query: str = None) -> bool:
        """키워드 매칭 확인"""
        text = f"{title} {content}".lower()

        # Check target keywords
        for keyword in get_all_keywords():
            if keyword.lower() in text:
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

    parser = argparse.ArgumentParser(description='Pharmaceutical Online Scraper (Hub-based)')
    parser.add_argument('--reset', action='store_true', help='Reset snapshot and create new baseline')
    parser.add_argument('--days', type=int, default=None, help='Override days_back (default: auto)')
    args = parser.parse_args()

    if args.reset:
        snapshot_file = os.path.join(SNAPSHOT_DIR, "article_links.json")
        if os.path.exists(snapshot_file):
            os.remove(snapshot_file)
            print("Snapshot reset. Next run will create new baseline.")

    scraper = PharmaceuticalOnlineScraper()
    articles = scraper.fetch_news(days_back=args.days)

    print(f"\nTotal collected: {len(articles)} new articles\n")

    for i, article in enumerate(articles[:10], 1):
        print(f"{i}. {article.title[:80]}...")
        print(f"   Published: {article.published}")
        print(f"   Keywords: {', '.join(article.matched_keywords[:5])}")
        print(f"   {article.link}")
        print()


if __name__ == "__main__":
    main()
