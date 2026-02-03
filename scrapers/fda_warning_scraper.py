# FDA Enforcement (Recalls) Scraper
# openFDA API를 사용한 FDA 리콜 및 규제 조치 스크래퍼

import requests
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    from base_scraper import BaseScraper, NewsArticle


class FDAEnforcementScraper(BaseScraper):
    """
    FDA Enforcement (Recalls) 스크래퍼
    
    openFDA API를 사용하여 FDA 규제 조치 데이터 수집
    - Drug recalls (의약품 리콜)
    - Device recalls (의료기기 리콜)
    - Food recalls (식품 리콜)
    
    API 문서: https://open.fda.gov/apis/drug/enforcement/
    """
    
    # openFDA API 엔드포인트
    API_BASE = "https://api.fda.gov"
    
    # 엔드포인트 목록
    ENDPOINTS = {
        "drug": "/drug/enforcement.json",
        "device": "/device/enforcement.json",
        "food": "/food/enforcement.json"
    }
    
    def __init__(self, category: str = "drug"):
        """
        FDA Enforcement 스크래퍼 초기화
        
        Args:
            category: 수집할 카테고리 ("drug", "device", "food", 또는 "all")
        """
        self.category = category.lower()
        self.api_key = os.environ.get("OPENFDA_API_KEY", "")
    
    @property
    def source_name(self) -> str:
        if self.category == "all":
            return "FDA Enforcement Actions"
        return f"FDA {self.category.capitalize()} Recalls"
    
    @property
    def base_url(self) -> str:
        return "https://www.fda.gov"
    
    def _get_days_back(self) -> int:
        """
        요일에 따른 수집 기간 결정
        FDA는 매일 업데이트되지 않으므로 더 긴 기간 조회
        이미 보고된 항목은 AI 시스템이 자동으로 중복 제거
        """
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return 14  # 2주
        return 14  # 평일도 2주 (FDA recalls are infrequent, dedupe handled by email system)
    
    def _build_api_url(self, endpoint: str, days_back: int, limit: int = 100) -> str:
        """API URL 생성"""
        url = f"{self.API_BASE}{endpoint}"
        
        # 날짜 범위 쿼리
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        date_query = f'report_date:[{start_date.strftime("%Y%m%d")}+TO+{end_date.strftime("%Y%m%d")}]'
        
        params = [
            f"search={date_query}",
            f"limit={limit}",
            "sort=report_date:desc"
        ]
        
        # API 키 추가 (있는 경우)
        if self.api_key:
            params.append(f"api_key={self.api_key}")
        
        return f"{url}?{'&'.join(params)}"
    
    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        FDA 규제 조치 수집
        
        Args:
            query: 검색 키워드 (선택적 - 제품명/회사명 필터)
            days_back: 수집 기간 (None이면 자동 계산)
            
        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        print(f"[FDA] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        print(f"[FDA] Category: {self.category}")
        if self.api_key:
            print(f"[FDA] Using API key: {self.api_key[:8]}...")
        
        articles = []
        
        # 수집할 엔드포인트 결정
        if self.category == "all":
            endpoints = self.ENDPOINTS.items()
        elif self.category in self.ENDPOINTS:
            endpoints = [(self.category, self.ENDPOINTS[self.category])]
        else:
            print(f"[FDA] Unknown category: {self.category}")
            return []
        
        for cat_name, endpoint in endpoints:
            try:
                url = self._build_api_url(endpoint, days_back)
                print(f"[FDA] Fetching {cat_name} from API...")
                
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                
                if response.status_code == 404:
                    print(f"[FDA] No {cat_name} recalls found in date range")
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                print(f"[FDA] Found {len(results)} {cat_name} recalls")
                
                for item in results:
                    article = self._parse_result(item, cat_name, query)
                    if article:
                        articles.append(article)
                        
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"[FDA] No {cat_name} recalls in date range")
                else:
                    print(f"[FDA] API error for {cat_name}: {e}")
            except Exception as e:
                print(f"[FDA] Error fetching {cat_name}: {e}")
        
        print(f"[FDA] Total collected: {len(articles)} enforcement actions")
        return articles
    
    def _parse_result(self, item: dict, category: str, query: str = None) -> Optional[NewsArticle]:
        """API 결과 파싱"""
        try:
            # 필수 필드 추출
            recall_number = item.get("recall_number", "Unknown")
            product_description = item.get("product_description", "")
            reason = item.get("reason_for_recall", "")
            company = item.get("recalling_firm", "Unknown Company")
            classification = item.get("classification", "")  # Class I, II, III
            status = item.get("status", "")
            
            # 날짜 파싱
            report_date = item.get("report_date", "")
            published = None
            if report_date:
                try:
                    published = datetime.strptime(report_date, "%Y%m%d")
                except:
                    pass
            
            # 키워드 필터링
            if query:
                search_text = f"{product_description} {company} {reason}".lower()
                if query.lower() not in search_text:
                    return None
            
            # 제목 생성
            title = f"[FDA {category.upper()} Recall] {company} - {product_description[:50]}"
            
            # 요약
            summary = f"Company: {company}\nProduct: {product_description[:200]}\nReason: {reason}\nClassification: {classification}\nStatus: {status}"
            
            # 링크 (FDA Recall 페이지)
            link = f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfres/res.cfm?id={recall_number}"
            
            # 분류
            classifications, matched_keywords = classify_article(title, summary)
            if not classifications:
                classifications = ["FDA", "규제", "리콜", category]
                matched_keywords = ["FDA", classification, category]
            
            return NewsArticle(
                title=title,
                link=link,
                published=published,
                source=f"FDA {category.capitalize()}",
                summary=summary,
                full_text=f"Product: {product_description}\n\nReason for Recall: {reason}\n\nRecalling Firm: {company}\n\nClassification: {classification}",
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords
            )
            
        except Exception as e:
            return None


# 별칭 변경: 이 파일은 이제 FDA Drug Recalls만 담당
# Warning Letters는 fda_warning_letters_scraper.py 참조
FDARecallsScraper = FDAEnforcementScraper
FDAWarningLettersScraper = FDAEnforcementScraper  # 하위 호환성 유지


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FDA Enforcement (Recalls) Scraper")
    parser.add_argument("--category", default="drug",
                       help="Category: drug, device, food, or all")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 1 day or 3 on Monday)")
    args = parser.parse_args()
    
    scraper = FDAEnforcementScraper(category=args.category)
    
    print("=" * 60)
    print("FDA Enforcement Scraper (openFDA API)")
    print("=" * 60)
    
    articles = scraper.fetch_news(days_back=args.days)
    
    print(f"\nTotal collected: {len(articles)} enforcement actions\n")
    
    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:60]}...")
        print(f"   {article.link}")
        print()
