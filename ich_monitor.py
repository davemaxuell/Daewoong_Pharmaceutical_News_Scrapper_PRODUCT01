# ICH Guidelines Monitor
# ICH 가이드라인 변경 모니터링 시스템

import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import json
import os
import re


class ICHGuidelinesMonitor:
    """
    ICH Guidelines 변경 모니터
    
    ICH 웹페이지의 변경 사항을 감지합니다.
    API 응답의 해시를 비교하여 변경 여부를 판단합니다.
    
    지원 가이드라인:
    - Quality (Q1-Q14)
    - Safety (S1-S11)
    - Efficacy (E1-E20)
    - Multidisciplinary (M1-M13)
    """
    
    # API 엔드포인트
    API_BASE = "https://admin.ich.org/api/v1/nodes"
    
    # 가이드라인 페이지 별칭
    GUIDELINE_PAGES = {
        "quality": "/page/quality-guidelines",
        "safety": "/page/safety-guidelines",
        "efficacy": "/page/efficacy-guidelines",
        "multidisciplinary": "/page/multidisciplinary-guidelines",
    }
    
    def __init__(self, storage_dir: str = None):
        """
        Args:
            storage_dir: 스냅샷 저장 디렉토리
        """
        self.storage_dir = storage_dir or os.path.dirname(os.path.abspath(__file__))
        self.snapshots_dir = os.path.join(self.storage_dir, ".ich_snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)
    
    def _get_headers(self) -> dict:
        """HTTP 요청 헤더"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
    
    def _get_snapshot_path(self, category: str) -> str:
        """스냅샷 파일 경로"""
        return os.path.join(self.snapshots_dir, f"ich_{category}_snapshot.json")
    
    def fetch_api_data(self, category: str = "quality") -> Dict[str, Any]:
        """
        ICH API에서 가이드라인 데이터 가져오기
        """
        if category not in self.GUIDELINE_PAGES:
            raise ValueError(f"Unknown category: {category}")
        
        alias = self.GUIDELINE_PAGES[category]
        url = f"{self.API_BASE}?loadEntities[]=paragraph&alias={alias}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[ICH Monitor] API error: {e}")
            return {}
    
    def extract_info(self, api_data: Dict, category: str) -> Dict[str, Any]:
        """
        API 응답에서 정보 추출
        """
        info = {
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "content_hash": "",
            "guidelines_found": [],
            "links_found": []
        }
        
        # 전체 응답을 문자열로 변환하여 해시 생성
        content_str = json.dumps(api_data, sort_keys=True)
        info["content_hash"] = hashlib.sha256(content_str.encode()).hexdigest()
        info["response_size"] = len(content_str)
        
        # 가이드라인 ID 패턴 찾기 (Q1, Q2, S1, E1, M1 등)
        guideline_pattern = rf'[{category[0].upper()}]\d+[A-Z]?'
        guidelines = set(re.findall(guideline_pattern, content_str, re.IGNORECASE))
        info["guidelines_found"] = sorted(list(guidelines))
        
        # PDF/문서 링크 찾기
        pdf_pattern = r'https?://[^\s"\'<>]+\.pdf'
        pdfs = set(re.findall(pdf_pattern, content_str))
        info["links_found"] = list(pdfs)[:50]  # 최대 50개
        
        return info
    
    def save_snapshot(self, category: str, info: Dict[str, Any]) -> None:
        """스냅샷 저장"""
        path = self._get_snapshot_path(category)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(f"[ICH Monitor] Snapshot saved: {path}")
    
    def load_previous_snapshot(self, category: str) -> Optional[Dict[str, Any]]:
        """이전 스냅샷 로드"""
        path = self._get_snapshot_path(category)
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
            "new_links": [],
            "removed_links": [],
            "summary": ""
        }
        
        # 해시 비교
        if old.get("content_hash") == new.get("content_hash"):
            changes["summary"] = "No changes detected"
            return changes
        
        changes["has_changes"] = True
        
        # 링크 변경
        old_links = set(old.get("links_found", []))
        new_links = set(new.get("links_found", []))
        
        changes["new_links"] = list(new_links - old_links)
        changes["removed_links"] = list(old_links - new_links)
        
        # 가이드라인 변경
        old_guides = set(old.get("guidelines_found", []))
        new_guides = set(new.get("guidelines_found", []))
        
        changes["new_guidelines"] = list(new_guides - old_guides)
        changes["removed_guidelines"] = list(old_guides - new_guides)
        
        # 크기 변경
        old_size = old.get("response_size", 0)
        new_size = new.get("response_size", 0)
        size_diff = new_size - old_size
        
        # 요약
        parts = []
        if changes["new_links"]:
            parts.append(f"{len(changes['new_links'])} new PDFs")
        if changes["removed_links"]:
            parts.append(f"{len(changes['removed_links'])} removed PDFs")
        if changes["new_guidelines"]:
            parts.append(f"New: {', '.join(changes['new_guidelines'])}")
        if size_diff != 0:
            parts.append(f"Size diff: {size_diff:+d} bytes")
        
        changes["summary"] = ", ".join(parts) if parts else "Content modified"
        
        return changes
    
    def check_category(self, category: str = "quality") -> Dict[str, Any]:
        """특정 카테고리 체크"""
        print(f"[ICH Monitor] Checking {category} guidelines...")
        
        # API 데이터 가져오기
        api_data = self.fetch_api_data(category)
        if not api_data:
            return {
                "category": category,
                "status": "error",
                "error": "Failed to fetch API data",
                "has_changes": False
            }
        
        # 정보 추출
        current_info = self.extract_info(api_data, category)
        
        # 이전 스냅샷
        previous_info = self.load_previous_snapshot(category)
        
        if not previous_info:
            self.save_snapshot(category, current_info)
            return {
                "category": category,
                "status": "first_check",
                "message": "First check - baseline saved",
                "guidelines_count": len(current_info.get("guidelines_found", [])),
                "links_count": len(current_info.get("links_found", [])),
                "has_changes": False
            }
        
        # 변경 비교
        changes = self.compare_snapshots(previous_info, current_info)
        
        # 변경이 있으면 새 스냅샷 저장
        if changes["has_changes"]:
            self.save_snapshot(category, current_info)
        
        return {
            "category": category,
            "status": "checked",
            **changes
        }
    
    def check_all(self) -> List[Dict[str, Any]]:
        """모든 카테고리 체크"""
        results = []
        
        print("=" * 60)
        print("ICH Guidelines Change Monitor")
        print("=" * 60)
        
        for category in self.GUIDELINE_PAGES.keys():
            result = self.check_category(category)
            results.append(result)
            
            status = result.get("status", "")
            if result.get("has_changes"):
                print(f"  [{category.upper()}] CHANGES: {result.get('summary')}")
            elif status == "first_check":
                print(f"  [{category.upper()}] First check - baseline saved")
            elif status == "error":
                print(f"  [{category.upper()}] Error: {result.get('error')}")
            else:
                print(f"  [{category.upper()}] No changes")
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """변경 리포트 생성"""
        lines = [
            "=" * 60,
            "ICH GUIDELINES CHANGE REPORT",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            ""
        ]
        
        changes_found = False
        
        for result in results:
            category = result.get("category", "unknown").upper()
            lines.append(f"[{category}]")
            lines.append("-" * 40)
            
            if result.get("has_changes"):
                changes_found = True
                lines.append(f"CHANGES: {result.get('summary')}")
                
                for link in result.get("new_links", [])[:3]:
                    lines.append(f"  + {link[-60:]}")
            
            elif result.get("status") == "first_check":
                lines.append(f"First check - baseline saved")
            
            elif result.get("status") == "error":
                lines.append(f"Error: {result.get('error')}")
            
            else:
                lines.append("No changes")
            
            lines.append("")
        
        lines.append("=" * 60)
        if changes_found:
            lines.append("ACTION REQUIRED: Review changes")
        else:
            lines.append("All ICH guidelines unchanged")
        
        return "\n".join(lines)


# 독립 실행
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ICH Guidelines Monitor")
    parser.add_argument("--category", 
                       choices=["quality", "safety", "efficacy", "multidisciplinary", "all"],
                       default="quality",
                       help="Category to check")
    args = parser.parse_args()
    
    monitor = ICHGuidelinesMonitor()
    
    if args.category == "all":
        results = monitor.check_all()
        print("\n" + monitor.generate_report(results))
    else:
        result = monitor.check_category(args.category)
        print(f"\nResult: {json.dumps(result, indent=2, default=str)}")
