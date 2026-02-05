# GMP Journal EU GMP Annex 1 해석 모니터
# ECA/GMP Journal의 Annex 1 관련 기사 및 페이지 변경 감지

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import json
import os
import re


class GMPJournalAnnex1Monitor:
    """
    GMP Journal Annex 1 모니터

    EU GMP Annex 1 (무균 의약품 제조) 해석 관련 콘텐츠 모니터링:
    1. Annex 1 관련 새 기사 감지
    2. 주요 Annex 1 해석 페이지 변경 감지

    URL: https://www.gmp-journal.com/
    """

    BASE_URL = "https://www.gmp-journal.com"
    SEARCH_URL = f"{BASE_URL}/search-result.html?keywords=annex+1"

    # 모니터링할 주요 Annex 1 해석 페이지
    MONITORED_PAGES = [
        "/current-articles/details/annex-1-revision.html",
        "/current-articles/details/consequences-of-annex-1-revision-for-industry.html",
        "/current-articles/details/gmp-trends-annex-1-continuous-production-and-control-of-parenterals.html",
    ]

    def __init__(self, storage_dir: str = None):
        """
        Args:
            storage_dir: 스냅샷 저장 디렉토리
        """
        self.storage_dir = storage_dir or os.path.dirname(os.path.abspath(__file__))
        self.snapshots_dir = os.path.join(self.storage_dir, ".gmpjournal_snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def _get_headers(self) -> dict:
        """HTTP 요청 헤더"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def _get_snapshot_path(self) -> str:
        """스냅샷 파일 경로"""
        return os.path.join(self.snapshots_dir, "annex1_snapshot.json")

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """페이지 가져오기"""
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=60)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"[GMP Journal Annex1] Page fetch error ({url}): {e}")
            return None

    def extract_search_articles(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        검색 결과 페이지에서 Annex 1 관련 기사 추출
        """
        articles = []

        # 기사 목록 (div.even, div.odd)
        for item in soup.select('div.even, div.odd'):
            try:
                # 제목과 링크
                title_link = item.select_one('h2 > a') or item.select_one('h3 > a')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                href = title_link.get('href', '')

                if not title or not href:
                    continue

                # 절대 URL 생성
                if href.startswith('/'):
                    full_link = f"{self.BASE_URL}{href}"
                elif not href.startswith('http'):
                    full_link = f"{self.BASE_URL}/{href}"
                else:
                    full_link = href

                # 날짜 추출
                date_str = ""
                time_elem = item.select_one('time[datetime]')
                if time_elem:
                    date_str = time_elem.get('datetime', '')[:10]  # YYYY-MM-DD
                else:
                    info_elem = item.select_one('p.info')
                    if info_elem:
                        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', info_elem.get_text())
                        if date_match:
                            d, m, y = date_match.groups()
                            date_str = f"{y}-{m}-{d}"

                articles.append({
                    "title": title,
                    "url": full_link,
                    "date": date_str,
                    "hash": hashlib.md5(full_link.encode()).hexdigest()[:8]
                })

            except Exception as e:
                continue

        return articles

    def extract_page_content_hash(self, url: str) -> Optional[str]:
        """
        특정 페이지의 본문 콘텐츠 해시 추출
        """
        soup = self.fetch_page(url)
        if not soup:
            return None

        # 본문 콘텐츠 추출
        content = ""
        for selector in ['.article-body', '.content-body', 'article', 'main', '.main-content']:
            elem = soup.select_one(selector)
            if elem:
                # 스크립트, 스타일 제거
                for tag in elem.find_all(['script', 'style', 'nav', 'footer']):
                    tag.decompose()
                content = elem.get_text(separator=' ', strip=True)
                if len(content) > 200:
                    break

        if not content:
            # Fallback: 전체 body
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)

        return hashlib.sha256(content.encode()).hexdigest()

    def collect_current_data(self) -> Dict[str, Any]:
        """
        현재 상태 수집
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "articles": [],
            "page_hashes": {},
            "article_count": 0
        }

        # 1. Annex 1 검색 결과에서 기사 목록 수집
        print("[GMP Journal Annex1] Fetching Annex 1 articles...")
        soup = self.fetch_page(self.SEARCH_URL)
        if soup:
            data["articles"] = self.extract_search_articles(soup)
            data["article_count"] = len(data["articles"])
            print(f"  -> Found {data['article_count']} Annex 1 articles")

        # 2. 주요 페이지 콘텐츠 해시 수집
        print("[GMP Journal Annex1] Checking monitored pages...")
        for page_path in self.MONITORED_PAGES:
            url = f"{self.BASE_URL}{page_path}"
            page_hash = self.extract_page_content_hash(url)
            if page_hash:
                data["page_hashes"][page_path] = page_hash

        print(f"  -> Monitored {len(data['page_hashes'])} pages")

        return data

    def save_snapshot(self, data: Dict[str, Any]) -> None:
        """스냅샷 저장"""
        path = self._get_snapshot_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[GMP Journal Annex1] Snapshot saved: {path}")

    def load_previous_snapshot(self) -> Optional[Dict[str, Any]]:
        """이전 스냅샷 로드"""
        path = self._get_snapshot_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def compare_snapshots(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """두 스냅샷 비교"""
        changes = {
            "has_changes": False,
            "old_timestamp": old.get("timestamp"),
            "new_timestamp": new.get("timestamp"),
            "new_articles": [],
            "removed_articles": [],
            "modified_pages": [],
            "summary": ""
        }

        # 1. 기사 비교 (URL 기준)
        old_urls = {a["url"] for a in old.get("articles", [])}
        new_urls = {a["url"] for a in new.get("articles", [])}

        added_urls = new_urls - old_urls
        removed_urls = old_urls - new_urls

        # 새로 추가된 기사
        for article in new.get("articles", []):
            if article["url"] in added_urls:
                changes["new_articles"].append(article)

        # 삭제된 기사
        for article in old.get("articles", []):
            if article["url"] in removed_urls:
                changes["removed_articles"].append(article)

        # 2. 페이지 콘텐츠 변경 비교
        old_hashes = old.get("page_hashes", {})
        new_hashes = new.get("page_hashes", {})

        for page_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(page_path)
            if old_hash and old_hash != new_hash:
                changes["modified_pages"].append({
                    "path": page_path,
                    "url": f"{self.BASE_URL}{page_path}",
                    "change_type": "content_modified"
                })

        # 변경 여부 확인
        if changes["new_articles"] or changes["removed_articles"] or changes["modified_pages"]:
            changes["has_changes"] = True

        # 요약 생성
        parts = []
        if changes["new_articles"]:
            parts.append(f"{len(changes['new_articles'])} new article(s)")
        if changes["removed_articles"]:
            parts.append(f"{len(changes['removed_articles'])} removed article(s)")
        if changes["modified_pages"]:
            parts.append(f"{len(changes['modified_pages'])} page(s) modified")

        changes["summary"] = ", ".join(parts) if parts else "No changes detected"

        return changes

    def check(self) -> Dict[str, Any]:
        """
        GMP Journal Annex 1 변경 체크
        """
        print("[GMP Journal Annex1] Checking EU GMP Annex 1 content...")

        # 현재 데이터 수집
        current_data = self.collect_current_data()

        if current_data["article_count"] == 0:
            return {
                "status": "error",
                "error": "Failed to fetch articles",
                "has_changes": False
            }

        # 이전 스냅샷 로드
        previous_data = self.load_previous_snapshot()

        if not previous_data:
            # 첫 번째 체크 - 베이스라인 저장
            self.save_snapshot(current_data)
            return {
                "status": "first_check",
                "message": "First check - baseline saved",
                "article_count": current_data["article_count"],
                "monitored_pages": len(current_data["page_hashes"]),
                "has_changes": False
            }

        # 변경 비교
        changes = self.compare_snapshots(previous_data, current_data)

        # 변경이 있으면 새 스냅샷 저장
        if changes["has_changes"]:
            self.save_snapshot(current_data)

        return {
            "status": "checked",
            **changes
        }

    def generate_report(self, result: Dict[str, Any]) -> str:
        """변경 리포트 생성"""
        lines = [
            "=" * 60,
            "GMP JOURNAL ANNEX 1 CHANGE REPORT",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Search URL: {self.SEARCH_URL}",
            "=" * 60,
            ""
        ]

        if result.get("status") == "error":
            lines.append(f"ERROR: {result.get('error')}")

        elif result.get("status") == "first_check":
            lines.append("First check - baseline saved")
            lines.append(f"Total Annex 1 articles: {result.get('article_count', 0)}")
            lines.append(f"Monitored pages: {result.get('monitored_pages', 0)}")

        elif result.get("has_changes"):
            lines.append("⚠️ CHANGES DETECTED")
            lines.append("-" * 40)
            lines.append(f"Summary: {result.get('summary')}")
            lines.append("")

            if result.get("new_articles"):
                lines.append("NEW ARTICLES:")
                for article in result["new_articles"][:10]:
                    lines.append(f"  + [{article.get('date', 'N/A')}] {article['title'][:50]}")
                    lines.append(f"    {article['url']}")

            if result.get("modified_pages"):
                lines.append("")
                lines.append("MODIFIED PAGES:")
                for page in result["modified_pages"]:
                    lines.append(f"  * {page['url']}")

            if result.get("removed_articles"):
                lines.append("")
                lines.append("REMOVED ARTICLES:")
                for article in result["removed_articles"][:5]:
                    lines.append(f"  - {article['title'][:50]}")

        else:
            lines.append("✓ No changes detected")
            lines.append(f"Last check: {result.get('old_timestamp', 'N/A')}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# 독립 실행
if __name__ == "__main__":
    monitor = GMPJournalAnnex1Monitor()
    result = monitor.check()
    print(monitor.generate_report(result))
