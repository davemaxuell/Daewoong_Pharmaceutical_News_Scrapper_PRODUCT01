# HTML Change Monitor
# 웹 페이지 변경 감지 및 알림 시스템

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Dict, List, Any
import hashlib
import json
import os
import difflib
import re

# Playwright import (optional - for sites with bot protection)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class HTMLChangeMonitor:
    """
    HTML 페이지 변경 감지 모니터
    
    특정 웹 페이지의 변경 사항을 감지하고 변경 내용을 보고합니다.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Args:
            storage_dir: 이전 상태를 저장할 디렉토리 (기본값: 현재 디렉토리)
        """
        self.storage_dir = storage_dir or os.path.dirname(os.path.abspath(__file__))
        self.snapshots_dir = os.path.join(self.storage_dir, ".page_snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)
    
    def _get_snapshot_path(self, url: str) -> str:
        """URL에 대한 스냅샷 파일 경로 생성"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return os.path.join(self.snapshots_dir, f"snapshot_{url_hash}.json")
    
    def _get_headers(self) -> dict:
        """HTTP 요청 헤더"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch_page_content(self, url: str, content_selector: str = None) -> Dict[str, Any]:
        """
        페이지 콘텐츠 가져오기
        
        Args:
            url: 모니터링할 URL
            content_selector: 모니터링할 특정 요소 선택자 (None이면 전체 body)
            
        Returns:
            페이지 콘텐츠 정보 딕셔너리
        """
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 특정 선택자가 있으면 해당 요소만 추출
            if content_selector:
                content_elem = soup.select_one(content_selector)
                if not content_elem:
                    print(f"[Monitor] Warning: Selector '{content_selector}' not found, using body")
                    content_elem = soup.body
            else:
                content_elem = soup.body
            
            # HTML 콘텐츠 추출
            html_content = str(content_elem) if content_elem else ""
            
            # 텍스트 콘텐츠 추출 (비교용)
            text_content = content_elem.get_text(separator="\n", strip=True) if content_elem else ""
            
            # 링크 추출
            links = []
            if content_elem:
                for link in content_elem.select('a[href]'):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if href and text:
                        links.append({
                            "text": text,
                            "href": href
                        })
            
            # 콘텐츠 해시 생성
            content_hash = hashlib.sha256(text_content.encode()).hexdigest()
            
            return {
                "url": url,
                "selector": content_selector,
                "timestamp": datetime.now().isoformat(),
                "html_content": html_content,
                "text_content": text_content,
                "links": links,
                "content_hash": content_hash,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def fetch_page_with_playwright(self, url: str, content_selector: str = None) -> Dict[str, Any]:
        """
        Playwright를 사용한 페이지 콘텐츠 가져오기 (봇 방지 우회)

        Args:
            url: 모니터링할 URL
            content_selector: 모니터링할 특정 요소 선택자

        Returns:
            페이지 콘텐츠 정보 딕셔너리
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": "Playwright not installed. Run: pip install playwright && playwright install chromium"
            }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate with timeout
                page.goto(url, timeout=60000, wait_until="networkidle")

                # Get page content
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')

            # 특정 선택자가 있으면 해당 요소만 추출
            if content_selector:
                content_elem = soup.select_one(content_selector)
                if not content_elem:
                    print(f"[Monitor] Warning: Selector '{content_selector}' not found, using body")
                    content_elem = soup.body
            else:
                content_elem = soup.body

            # HTML 콘텐츠 추출
            html_content = str(content_elem) if content_elem else ""

            # 텍스트 콘텐츠 추출 (비교용)
            text_content = content_elem.get_text(separator="\n", strip=True) if content_elem else ""

            # 링크 추출
            links = []
            if content_elem:
                for link in content_elem.select('a[href]'):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if href and text:
                        links.append({
                            "text": text,
                            "href": href
                        })

            # 콘텐츠 해시 생성
            content_hash = hashlib.sha256(text_content.encode()).hexdigest()

            return {
                "url": url,
                "selector": content_selector,
                "timestamp": datetime.now().isoformat(),
                "html_content": html_content,
                "text_content": text_content,
                "links": links,
                "content_hash": content_hash,
                "status": "success"
            }

        except Exception as e:
            return {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def save_snapshot(self, url: str, content: Dict[str, Any]) -> None:
        """스냅샷 저장"""
        snapshot_path = self._get_snapshot_path(url)
        
        # HTML 콘텐츠는 별도 저장 (JSON에서 제외하여 크기 줄임)
        save_data = {
            "url": content.get("url"),
            "selector": content.get("selector"),
            "timestamp": content.get("timestamp"),
            "text_content": content.get("text_content"),
            "links": content.get("links"),
            "content_hash": content.get("content_hash"),
            "status": content.get("status")
        }
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"[Monitor] Snapshot saved: {snapshot_path}")
    
    def load_previous_snapshot(self, url: str) -> Optional[Dict[str, Any]]:
        """이전 스냅샷 로드"""
        snapshot_path = self._get_snapshot_path(url)
        
        if os.path.exists(snapshot_path):
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def compare_content(self, old_content: Dict[str, Any], new_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        두 콘텐츠 비교
        
        Args:
            old_content: 이전 콘텐츠
            new_content: 새 콘텐츠
            
        Returns:
            변경 사항 딕셔너리
        """
        changes = {
            "has_changes": False,
            "old_timestamp": old_content.get("timestamp"),
            "new_timestamp": new_content.get("timestamp"),
            "text_changes": [],
            "link_changes": {"added": [], "removed": [], "modified": []},
            "summary": ""
        }
        
        # 해시 비교 (빠른 체크)
        if old_content.get("content_hash") == new_content.get("content_hash"):
            changes["summary"] = "No changes detected."
            return changes
        
        changes["has_changes"] = True
        
        # 텍스트 변경 비교
        old_text = old_content.get("text_content", "").split("\n")
        new_text = new_content.get("text_content", "").split("\n")
        
        diff = list(difflib.unified_diff(old_text, new_text, lineterm=''))
        
        added_lines = [line[1:] for line in diff if line.startswith('+') and not line.startswith('+++')]
        removed_lines = [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')]
        
        changes["text_changes"] = {
            "added": added_lines[:20],  # 최대 20개
            "removed": removed_lines[:20]
        }
        
        # 링크 변경 비교
        old_links = {(l["text"], l["href"]) for l in old_content.get("links", [])}
        new_links = {(l["text"], l["href"]) for l in new_content.get("links", [])}
        
        added_links = new_links - old_links
        removed_links = old_links - new_links
        
        changes["link_changes"]["added"] = [{"text": t, "href": h} for t, h in added_links]
        changes["link_changes"]["removed"] = [{"text": t, "href": h} for t, h in removed_links]
        
        # 요약 생성
        summary_parts = []
        if added_lines:
            summary_parts.append(f"{len(added_lines)} lines added")
        if removed_lines:
            summary_parts.append(f"{len(removed_lines)} lines removed")
        if added_links:
            summary_parts.append(f"{len(added_links)} links added")
        if removed_links:
            summary_parts.append(f"{len(removed_links)} links removed")
        
        changes["summary"] = ", ".join(summary_parts) if summary_parts else "Content modified"
        
        return changes
    
    def check_for_changes(self, url: str, content_selector: str = None, use_playwright: bool = False) -> Dict[str, Any]:
        """
        페이지 변경 확인 (주요 메서드)

        Args:
            url: 모니터링할 URL
            content_selector: 모니터링할 특정 요소 선택자
            use_playwright: Playwright 사용 여부 (봇 방지 사이트용)

        Returns:
            변경 사항 리포트 딕셔너리
        """
        print(f"[Monitor] Checking: {url}")

        # 현재 콘텐츠 가져오기
        if use_playwright:
            print(f"[Monitor] Using Playwright for bot-protected site")
            current_content = self.fetch_page_with_playwright(url, content_selector)
        else:
            current_content = self.fetch_page_content(url, content_selector)
        
        if current_content.get("status") == "error":
            return {
                "url": url,
                "status": "error",
                "error": current_content.get("error"),
                "timestamp": current_content.get("timestamp")
            }
        
        # 이전 스냅샷 로드
        previous_content = self.load_previous_snapshot(url)
        
        if not previous_content:
            # 첫 번째 모니터링 - 기준 스냅샷 저장
            self.save_snapshot(url, current_content)
            return {
                "url": url,
                "status": "first_check",
                "message": "First check - baseline snapshot saved",
                "timestamp": current_content.get("timestamp"),
                "has_changes": False
            }
        
        # 변경 비교
        changes = self.compare_content(previous_content, current_content)
        
        # 변경이 있으면 새 스냅샷 저장
        if changes["has_changes"]:
            self.save_snapshot(url, current_content)
        
        return {
            "url": url,
            "status": "checked",
            "timestamp": current_content.get("timestamp"),
            "previous_check": previous_content.get("timestamp"),
            **changes
        }
    
    def generate_change_report(self, changes: Dict[str, Any]) -> str:
        """
        변경 사항 리포트 생성
        
        Args:
            changes: compare_content 또는 check_for_changes 결과
            
        Returns:
            사람이 읽기 쉬운 리포트 문자열
        """
        lines = [
            "=" * 60,
            "PAGE CHANGE REPORT",
            "=" * 60,
            f"URL: {changes.get('url', 'N/A')}",
            f"Checked: {changes.get('timestamp', 'N/A')}",
            f"Previous: {changes.get('previous_check', 'N/A')}",
            ""
        ]
        
        if changes.get("status") == "first_check":
            lines.append("First check - baseline saved. No previous data to compare.")
            return "\n".join(lines)
        
        if changes.get("status") == "error":
            lines.append(f"ERROR: {changes.get('error', 'Unknown error')}")
            return "\n".join(lines)
        
        if not changes.get("has_changes"):
            lines.append("NO CHANGES DETECTED")
            return "\n".join(lines)
        
        lines.append(f"CHANGES DETECTED: {changes.get('summary', '')}")
        lines.append("")
        
        # 텍스트 변경
        text_changes = changes.get("text_changes", {})
        if text_changes.get("added"):
            lines.append("-" * 40)
            lines.append("ADDED LINES:")
            for line in text_changes["added"][:10]:
                lines.append(f"  + {line[:100]}")
            if len(text_changes["added"]) > 10:
                lines.append(f"  ... and {len(text_changes['added']) - 10} more")
        
        if text_changes.get("removed"):
            lines.append("-" * 40)
            lines.append("REMOVED LINES:")
            for line in text_changes["removed"][:10]:
                lines.append(f"  - {line[:100]}")
            if len(text_changes["removed"]) > 10:
                lines.append(f"  ... and {len(text_changes['removed']) - 10} more")
        
        # 링크 변경
        link_changes = changes.get("link_changes", {})
        if link_changes.get("added"):
            lines.append("-" * 40)
            lines.append("NEW LINKS:")
            for link in link_changes["added"][:10]:
                lines.append(f"  + [{link['text']}] -> {link['href']}")
        
        if link_changes.get("removed"):
            lines.append("-" * 40)
            lines.append("REMOVED LINKS:")
            for link in link_changes["removed"][:10]:
                lines.append(f"  - [{link['text']}] -> {link['href']}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# PMDA JP 페이지 전용 모니터
class PMDAJPMonitor(HTMLChangeMonitor):
    """
    PMDA Japanese Pharmacopoeia 페이지 전용 모니터
    """
    
    # 모니터링 대상 URL 목록
    MONITORED_PAGES = {
        "JP18": "https://www.pmda.go.jp/english/rs-sb-std/standards-development/jp/0029.html",
        "JP17": "https://www.pmda.go.jp/english/rs-sb-std/standards-development/jp/0019.html",
    }
    
    def __init__(self, storage_dir: str = None):
        super().__init__(storage_dir)
        self.content_selector = "main.main"  # PMDA 페이지 메인 콘텐츠 선택자
    
    def check_jp18(self) -> Dict[str, Any]:
        """JP18 페이지 변경 확인"""
        return self.check_for_changes(
            self.MONITORED_PAGES["JP18"],
            self.content_selector
        )
    
    def check_all(self) -> List[Dict[str, Any]]:
        """모든 JP 페이지 변경 확인"""
        results = []
        for name, url in self.MONITORED_PAGES.items():
            print(f"\n[Monitor] Checking {name}...")
            result = self.check_for_changes(url, self.content_selector)
            result["page_name"] = name
            results.append(result)
        return results
    
    def run_and_report(self, url: str = None) -> str:
        """
        모니터링 실행 및 리포트 생성
        
        Args:
            url: 특정 URL (None이면 JP18 기본)
            
        Returns:
            변경 사항 리포트 문자열
        """
        if not url:
            url = self.MONITORED_PAGES["JP18"]
        
        result = self.check_for_changes(url, self.content_selector)
        return self.generate_change_report(result)


# EudraLex Volume 4 페이지 전용 모니터
class EudraLexMonitor(HTMLChangeMonitor):
    """
    EudraLex Volume 4 (EU GMP Guidelines) 페이지 변경 모니터
    
    URL: https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en
    """
    
    MONITORED_URL = "https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en"
    
    def __init__(self, storage_dir: str = None):
        super().__init__(storage_dir)
        # ECL 레이아웃의 메인 콘텐츠 영역
        self.content_selector = "main"
    
    def check(self) -> Dict[str, Any]:
        """EudraLex 페이지 변경 확인"""
        return self.check_for_changes(self.MONITORED_URL, self.content_selector)
    
    def run_and_report(self) -> str:
        """모니터링 실행 및 리포트 생성"""
        result = self.check()
        return self.generate_change_report(result)


# 통합 모니터 - 모든 페이지 한번에 확인
class RegulatoryPageMonitor(HTMLChangeMonitor):
    """
    규제 페이지 통합 모니터
    PMDA JP + EudraLex + 기타 규제 사이트 모니터링
    """
    
    MONITORED_PAGES = {
        "PMDA_JP18": {
            "url": "https://www.pmda.go.jp/english/rs-sb-std/standards-development/jp/0029.html",
            "selector": "main.main",
            "description": "PMDA Japanese Pharmacopoeia 18th Edition"
        },
        "EudraLex_V4": {
            "url": "https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en",
            "selector": "main",
            "description": "EudraLex Volume 4 - EU GMP Guidelines"
        },
        "FDA_CGMP": {
            "url": "https://www.fda.gov/drugs/pharmaceutical-quality-resources/current-good-manufacturing-practice-cgmp-regulations",
            "selector": "main",
            "description": "FDA CGMP Regulations"
        },
        "USP_Pending": {
            "url": "https://www.uspnf.com/pending-monographs/pending-monograph-program",
            "selector": "main",
            "description": "USP Pending Monographs",
            "use_playwright": True
        },
        "USP_Bulletins": {
            "url": "https://www.uspnf.com/official-text/revision-bulletins",
            "selector": "main",
            "description": "USP Revision Bulletins",
            "use_playwright": True
        },
    }
    
    def check_all(self) -> List[Dict[str, Any]]:
        """모든 규제 페이지 변경 확인"""
        results = []

        print("=" * 60)
        print("Regulatory Page Change Monitor")
        print("=" * 60)

        for name, config in self.MONITORED_PAGES.items():
            print(f"\n[Monitor] Checking {name}...")
            print(f"  URL: {config['url']}")

            use_playwright = config.get('use_playwright', False)
            result = self.check_for_changes(config['url'], config['selector'], use_playwright=use_playwright)
            result["page_name"] = name
            result["description"] = config['description']
            results.append(result)
            
            # 결과 출력
            if result.get("has_changes"):
                print(f"  [CHANGE DETECTED] {result.get('summary')}")
            elif result.get("status") == "first_check":
                print(f"  [FIRST CHECK] Baseline saved")
            else:
                print(f"  [NO CHANGES]")
        
        return results
    
    def run_and_report_all(self) -> str:
        """모든 페이지 모니터링 및 통합 리포트 생성"""
        results = self.check_all()
        
        report_lines = [
            "=" * 60,
            "REGULATORY PAGE CHANGE REPORT",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            ""
        ]
        
        changes_found = False
        for result in results:
            name = result.get("page_name", "Unknown")
            desc = result.get("description", "")
            
            report_lines.append(f"[{name}] {desc}")
            report_lines.append("-" * 40)
            
            if result.get("has_changes"):
                changes_found = True
                report_lines.append(f"CHANGES DETECTED: {result.get('summary')}")
                
                # 추가된 링크 표시
                link_changes = result.get("link_changes", {})
                if link_changes.get("added"):
                    report_lines.append("New links:")
                    for link in link_changes["added"][:5]:
                        report_lines.append(f"  + {link['text'][:50]}")
            elif result.get("status") == "first_check":
                report_lines.append("First check - baseline saved")
            else:
                report_lines.append("No changes detected")
            
            report_lines.append("")
        
        report_lines.append("=" * 60)
        if changes_found:
            report_lines.append("ACTION REQUIRED: Review changes above")
        else:
            report_lines.append("All pages unchanged")
        
        return "\n".join(report_lines)


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Regulatory Page Change Monitor")
    parser.add_argument("--page", choices=["pmda", "eudralex", "all"], default="all",
                       help="Page to monitor")
    args = parser.parse_args()
    
    if args.page == "pmda":
        monitor = PMDAJPMonitor()
        report = monitor.run_and_report()
    elif args.page == "eudralex":
        monitor = EudraLexMonitor()
        report = monitor.run_and_report()
    else:
        monitor = RegulatoryPageMonitor()
        report = monitor.run_and_report_all()
    
    print(report)

