# Pharmaceutical Online Scraper
# Uses snapshot-based change detection (like PMDA/USP monitors)
# https://www.pharmaceuticalonline.com/

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional, Set
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
    Pharmaceutical Online 스크래퍼 (스냅샷 기반 변경 감지)

    작동 방식:
    1. 모든 카테고리에서 기사 링크 수집
    2. 이전 스냅샷과 비교하여 새 기사만 식별
    3. 새 기사만 상세 정보 수집
    4. 스냅샷 업데이트

    수집 소스 (10개):
    1. https://www.pharmaceuticalonline.com/ (메인)
    2. https://www.pharmaceuticalonline.com/solution/critical-environments (클린룸/제조환경)
    3. https://www.pharmaceuticalonline.com/solution/solid-dose-manufacturing (고형제 제조)
    4. https://www.pharmaceuticalonline.com/solution/liquid-dose-manufacturing (액제 제조)
    5. https://www.pharmaceuticalonline.com/solution/inspection (검사)
    6. https://www.pharmaceuticalonline.com/solution/serialization (시리얼화)
    7. https://www.pharmaceuticalonline.com/solution/packaging (포장)
    8. https://www.pharmaceuticalonline.com/solution/regulatory-compliance (규제 준수)
    9. https://www.pharmaceuticalonline.com/solution/quality-assurance (QA)
    10. https://www.pharmaceuticalonline.com/solution/quality-control (QC)

    키워드: keywords.py의 공통 키워드 사용
    """

    BASE_URL = "https://www.pharmaceuticalonline.com"

    # 타겟 카테고리 (완제의약품 공장 실무 관련)
    TARGET_CATEGORIES = [
        "/",  # Homepage - has recent articles
        "/solution/regulatory-compliance",
        "/solution/quality-assurance",
        "/solution/quality-control",
        "/solution/critical-environments",
        "/solution/solid-dose-manufacturing",
        "/solution/liquid-dose-manufacturing",
        "/solution/production",
        "/solution/inspection",
        "/solution/serialization",
        "/solution/packaging",
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

    def _save_snapshot(self, links: Set[str]):
        """Save current article links snapshot"""
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        snapshot_file = os.path.join(SNAPSHOT_DIR, "article_links.json")

        data = {
            "updated": datetime.now().isoformat(),
            "count": len(links),
            "links": list(links)
        }

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[Pharmaceutical Online] Snapshot updated: {len(links)} links")

    def _collect_all_links(self) -> Set[str]:
        """Collect all article links from all categories"""
        all_links = set()

        # Create session for cookie persistence
        session = requests.Session()
        session.headers.update(self.get_headers())

        for category in self.TARGET_CATEGORIES:
            try:
                url = f"{self.BASE_URL}{category}"
                print(f"[Pharmaceutical Online] Scanning: {url}")

                time.sleep(1)  # Polite delay
                response = session.get(url, timeout=30)

                if response.status_code != 200:
                    print(f"[Pharmaceutical Online] HTTP {response.status_code} for {category}")
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')

                # Find all /doc/ links
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if '/doc/' in href:
                        # Normalize URL
                        if href.startswith('/'):
                            href = f"{self.BASE_URL}{href}"
                        elif not href.startswith('http'):
                            href = f"{self.BASE_URL}/{href}"

                        # Only include pharmaceuticalonline.com links
                        if 'pharmaceuticalonline.com' in href:
                            all_links.add(href)

                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"[Pharmaceutical Online] Error scanning {category}: {e}")
                continue

        print(f"[Pharmaceutical Online] Total links found: {len(all_links)}")
        return all_links

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        Pharmaceutical Online에서 새 기사 수집 (스냅샷 기반)

        Args:
            query: 추가 검색 키워드 (선택)
            days_back: 사용하지 않음 (스냅샷 기반)

        Returns:
            NewsArticle 리스트 (새 기사만)
        """
        print(f"[Pharmaceutical Online] Starting snapshot-based scrape...")

        # Load previous snapshot
        previous_links = self._load_snapshot()
        is_first_run = len(previous_links) == 0

        if is_first_run:
            print(f"[Pharmaceutical Online] First run - creating baseline snapshot")
        else:
            print(f"[Pharmaceutical Online] Previous snapshot: {len(previous_links)} links")

        # Collect current links from all categories
        current_links = self._collect_all_links()

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
            # Update snapshot anyway (in case some links were removed)
            self._save_snapshot(current_links)
            return []

        print(f"[Pharmaceutical Online] Found {len(new_links)} NEW articles!")

        # Fetch details for new articles only
        articles = []
        session = requests.Session()
        session.headers.update(self.get_headers())

        for i, link in enumerate(new_links, 1):
            try:
                print(f"[Pharmaceutical Online] [{i}/{len(new_links)}] Fetching: {link[:60]}...")
                article = self._parse_article(session, link, query)
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

        # Update snapshot with all current links
        self._save_snapshot(current_links)

        print(f"[Pharmaceutical Online] Total collected: {len(articles)} new articles")
        return articles

    def _parse_article(self, session: requests.Session, link: str, query: str = None) -> Optional[NewsArticle]:
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

            # Extract author/source
            author = None
            for selector in ['.author', '.byline', 'meta[name="author"]']:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.get('content') or author_elem.get_text(strip=True)
                    break

            # Build title prefix
            title_prefix = "[Pharmaceutical Online]"
            if author:
                title_prefix = f"[Pharmaceutical Online - {author}]"

            return NewsArticle(
                title=f"{title_prefix} {title}",
                link=link,
                published=datetime.now(),  # Use current time as "discovered" time
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

    parser = argparse.ArgumentParser(description='Pharmaceutical Online Scraper (Snapshot-based)')
    parser.add_argument('--reset', action='store_true', help='Reset snapshot and create new baseline')
    args = parser.parse_args()

    if args.reset:
        snapshot_file = os.path.join(SNAPSHOT_DIR, "article_links.json")
        if os.path.exists(snapshot_file):
            os.remove(snapshot_file)
            print("Snapshot reset. Next run will create new baseline.")

    scraper = PharmaceuticalOnlineScraper()
    articles = scraper.fetch_news()

    print(f"\nTotal collected: {len(articles)} new articles\n")

    for i, article in enumerate(articles[:10], 1):
        print(f"{i}. {article.title[:80]}...")
        print(f"   Keywords: {', '.join(article.matched_keywords[:5])}")
        print(f"   {article.link}")
        print()


if __name__ == "__main__":
    main()
