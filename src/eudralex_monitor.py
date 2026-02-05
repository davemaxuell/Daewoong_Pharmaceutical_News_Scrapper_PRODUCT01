# EudraLex Volume 4 Document Change Monitor
# EU GMP 가이드라인 문서 변경 모니터링

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import json
import os
import re


class EudraLexMonitor:
    """
    EudraLex Volume 4 문서 변경 모니터

    EU GMP 가이드라인 페이지의 문서 변경 사항을 감지합니다.
    - Part I-IV 챕터
    - Annexes 1-21
    - PDF 링크 변경
    - 새 문서 추가/삭제

    URL: https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en
    """

    PAGE_URL = "https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en"

    def __init__(self, storage_dir: str = None):
        """
        Args:
            storage_dir: 스냅샷 저장 디렉토리
        """
        self.storage_dir = storage_dir or os.path.dirname(os.path.abspath(__file__))
        self.snapshots_dir = os.path.join(self.storage_dir, ".eudralex_snapshots")
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
        return os.path.join(self.snapshots_dir, "eudralex_vol4_snapshot.json")

    def fetch_page(self) -> Optional[BeautifulSoup]:
        """페이지 가져오기"""
        try:
            response = requests.get(self.PAGE_URL, headers=self._get_headers(), timeout=60)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"[EudraLex Monitor] Page fetch error: {e}")
            return None

    def extract_documents(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        페이지에서 문서 정보 추출
        """
        documents = {
            "timestamp": datetime.now().isoformat(),
            "parts": {},
            "annexes": {},
            "all_pdfs": [],
            "content_hash": ""
        }

        # 모든 PDF 링크 추출
        pdf_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '.pdf' in href.lower():
                text = link.get_text(strip=True)
                pdf_links.append({
                    "title": text,
                    "url": href,
                    "hash": hashlib.md5(href.encode()).hexdigest()[:8]
                })

        documents["all_pdfs"] = pdf_links

        # 섹션별 문서 추출
        # Part I, II, III, IV 및 Annexes 찾기
        sections = soup.find_all(['h2', 'h3', 'h4'])

        current_section = None
        for section in sections:
            text = section.get_text(strip=True).lower()

            # Part 감지
            if 'part i' in text and 'part ii' not in text:
                current_section = "part_i"
                documents["parts"]["Part I - Basic Requirements"] = []
            elif 'part ii' in text and 'part iii' not in text:
                current_section = "part_ii"
                documents["parts"]["Part II - Active Substances"] = []
            elif 'part iii' in text:
                current_section = "part_iii"
                documents["parts"]["Part III - GMP Related Documents"] = []
            elif 'part iv' in text:
                current_section = "part_iv"
                documents["parts"]["Part IV - ATMPs"] = []
            elif 'annex' in text:
                current_section = "annexes"
                # Annex 번호 추출
                annex_match = re.search(r'annex\s*(\d+)', text, re.IGNORECASE)
                if annex_match:
                    annex_num = annex_match.group(1)
                    documents["annexes"][f"Annex {annex_num}"] = section.get_text(strip=True)

        # 전체 콘텐츠 해시 생성
        content_str = json.dumps(pdf_links, sort_keys=True)
        documents["content_hash"] = hashlib.sha256(content_str.encode()).hexdigest()
        documents["pdf_count"] = len(pdf_links)

        return documents

    def save_snapshot(self, data: Dict[str, Any]) -> None:
        """스냅샷 저장"""
        path = self._get_snapshot_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[EudraLex Monitor] Snapshot saved: {path}")

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
            "new_pdfs": [],
            "removed_pdfs": [],
            "pdf_count_change": 0,
            "summary": ""
        }

        # 해시 비교
        if old.get("content_hash") == new.get("content_hash"):
            changes["summary"] = "No changes detected"
            return changes

        changes["has_changes"] = True

        # PDF 링크 비교
        old_urls = {p["url"] for p in old.get("all_pdfs", [])}
        new_urls = {p["url"] for p in new.get("all_pdfs", [])}

        added_urls = new_urls - old_urls
        removed_urls = old_urls - new_urls

        # 새로 추가된 PDF
        for pdf in new.get("all_pdfs", []):
            if pdf["url"] in added_urls:
                changes["new_pdfs"].append(pdf)

        # 삭제된 PDF
        for pdf in old.get("all_pdfs", []):
            if pdf["url"] in removed_urls:
                changes["removed_pdfs"].append(pdf)

        # PDF 개수 변화
        old_count = old.get("pdf_count", 0)
        new_count = new.get("pdf_count", 0)
        changes["pdf_count_change"] = new_count - old_count

        # 요약 생성
        parts = []
        if changes["new_pdfs"]:
            parts.append(f"{len(changes['new_pdfs'])} new PDF(s)")
        if changes["removed_pdfs"]:
            parts.append(f"{len(changes['removed_pdfs'])} removed PDF(s)")
        if changes["pdf_count_change"] != 0:
            parts.append(f"Total PDFs: {old_count} → {new_count}")

        changes["summary"] = ", ".join(parts) if parts else "Content modified"

        return changes

    def check(self) -> Dict[str, Any]:
        """
        EudraLex Volume 4 변경 체크
        """
        print("[EudraLex Monitor] Checking EudraLex Volume 4...")

        # 페이지 가져오기
        soup = self.fetch_page()
        if not soup:
            return {
                "status": "error",
                "error": "Failed to fetch page",
                "has_changes": False
            }

        # 문서 정보 추출
        current_data = self.extract_documents(soup)

        # 이전 스냅샷 로드
        previous_data = self.load_previous_snapshot()

        if not previous_data:
            # 첫 번째 체크 - 베이스라인 저장
            self.save_snapshot(current_data)
            return {
                "status": "first_check",
                "message": "First check - baseline saved",
                "pdf_count": current_data.get("pdf_count", 0),
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
            "EUDRALEX VOLUME 4 CHANGE REPORT",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"URL: {self.PAGE_URL}",
            "=" * 60,
            ""
        ]

        if result.get("status") == "error":
            lines.append(f"ERROR: {result.get('error')}")

        elif result.get("status") == "first_check":
            lines.append("First check - baseline saved")
            lines.append(f"Total PDFs found: {result.get('pdf_count', 0)}")

        elif result.get("has_changes"):
            lines.append("⚠️ CHANGES DETECTED")
            lines.append("-" * 40)
            lines.append(f"Summary: {result.get('summary')}")
            lines.append("")

            if result.get("new_pdfs"):
                lines.append("NEW DOCUMENTS:")
                for pdf in result["new_pdfs"][:10]:
                    lines.append(f"  + {pdf['title'][:60]}")
                    lines.append(f"    {pdf['url'][:70]}")

            if result.get("removed_pdfs"):
                lines.append("")
                lines.append("REMOVED DOCUMENTS:")
                for pdf in result["removed_pdfs"][:10]:
                    lines.append(f"  - {pdf['title'][:60]}")

        else:
            lines.append("✓ No changes detected")
            lines.append(f"Last check: {result.get('old_timestamp', 'N/A')}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# 독립 실행
if __name__ == "__main__":
    monitor = EudraLexMonitor()
    result = monitor.check()
    print(monitor.generate_report(result))
