# 다중 소스 스크래퍼
# 모든 뉴스 소스를 통합하여 수집하는 메인 스크래퍼

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 프로젝트 루트 설정 (src/ 상위 디렉토리)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


from scrapers.base_scraper import NewsArticle
from scrapers.kpanews_scraper import KPANewsScraper
from scrapers.kpbma_scraper import KPBMAScraper
from scrapers.edqm_scraper import EDQMScraper
from scrapers.mfds_scraper import MFDSScraper
from scrapers.eudralex_scraper import EudraLexScraper
from scrapers.pics_scraper import PICSScraper
from scrapers.dailypharm_scraper import DailyPharmScraper
from scrapers.yakup_scraper import YakupScraper
from scrapers.gmpjournal_scraper import GMPJournalScraper
from scrapers.pmda_scraper import PMDAScraper
from scrapers.ich_news_scraper import ICHScraper
from scrapers.fda_warning_scraper import FDAEnforcementScraper  # FDA Drug Recalls
from scrapers.fda_warning_letters_scraper import FDAWarningLettersScraper  # FDA Warning Letters
from scrapers.ispe_scraper import ISPEScraper  # ISPE 제약 엔지니어링
from scrapers.bioprocess_scraper import BioProcessScraper  # BioProcess QA/QC
from scrapers.pda_scraper import PDAScraper  # PDA Letter (주사제/무균공정)
from scrapers.pharmaceutical_online_scraper import PharmaceuticalOnlineScraper  # 완제의약품 제조 실무
# from scrapers.usp_monograph_scraper import USPMonographScraper  # PDF parsing, optional

import src.logger as logger  # Logging module


class MultiSourceScraper:
    """
    다중 소스 스크래퍼
    여러 뉴스 소스에서 동시에 수집하여 통합된 결과 제공
    """
    
    # 활성화된 스크래퍼 설정
    SCRAPERS_CONFIG = {
        # === 국내 뉴스 ===
        "kpa_news": {
            "class": KPANewsScraper,
            "enabled": True,
            "description": "약사공론 (KPA News)",
            "args": {}
        },
        "dailypharm": {
            "class": DailyPharmScraper,
            "enabled": True,
            "description": "데일리팜 (Daily Pharm) - 3개 카테고리: 메인, 정책·법률, 제약·바이오",
            "args": {}
        },
        "yakup": {
            "class": YakupScraper,
            "enabled": True,
            "description": "약업신문 (Yakup News)",
            "args": {}
        },
        "kpbma": {
            "class": KPBMAScraper,
            "enabled": True,
            "description": "한국제약바이오협회 뉴스레터",
            "args": {}
        },
        "mfds": {
            "class": MFDSScraper,
            "enabled": True,
            "description": "식품의약품안전처 RSS",
            "args": {"feeds": "main"}
        },
        # === 해외 규제 기관 ===
        "fda_recalls": {
            "class": FDAEnforcementScraper,
            "enabled": True,  # Re-enabled - working via openFDA API
            "description": "FDA Drug Recalls (openFDA API)",
            "args": {"category": "drug"},
            "use_internal_days_back": True  # FDA는 자체 14일 lookback 사용
        },
        "fda_warning_letters": {
            "class": FDAWarningLettersScraper,
            "enabled": True,  # Re-enabled - comprehensive coverage with Posted Date filtering
            "description": "FDA Warning Letters (All Offices)",
            "args": {"centers": ["ALL"]}  # Changed to ALL for comprehensive coverage
        },
        "pmda": {
            "class": PMDAScraper,
            "enabled": False,  # 분기별 업데이트 → monitor_pipeline으로 이동
            "description": "PMDA (일본 의약품규제) - Quarterly Newsletter",
            "args": {}
        },
        "edqm": {
            "class": EDQMScraper,
            "enabled": True,
            "description": "EDQM Newsrooms (EU)",
            "args": {"newsroom": "all"}
        },
        "eudralex": {
            "class": EudraLexScraper,
            "enabled": True,
            "description": "EudraLex Volume 4 (EU GMP)",
            "args": {}
        },
        # === 글로벌 GMP/품질 ===
        "pics": {
            "class": PICSScraper,
            "enabled": True,
            "description": "PIC/S (GMP Inspection)",
            "args": {}
        },
        "ich_news": {
            "class": ICHScraper,
            "enabled": True,
            "description": "ICH News (가이드라인)",
            "args": {}
        },
        "gmp_journal": {
            "class": GMPJournalScraper,
            "enabled": True,
            "description": "GMP Journal",
            "args": {}
        },
        "ispe": {
            "class": ISPEScraper,
            "enabled": True,
            "description": "ISPE (주사제/고형제 제조 공정, QA 이슈)",
            "args": {}
        },
        "bioprocess": {
            "class": BioProcessScraper,
            "enabled": True,
            "description": "BioProcess International (Validation, Fill-Finish, QA/QC)",
            "args": {}
        },
        "pda": {
            "class": PDAScraper,
            "enabled": True,
            "description": "PDA Letter (주사제/무균공정, 멸균, 바이오의약품)",
            "args": {}
        },
        "pharmaceutical_online": {
            "class": PharmaceuticalOnlineScraper,
            "enabled": True,
            "description": "Pharmaceutical Online (완제의약품 10개 카테고리: 고형제/액제, 검사, 포장, 시리얼화, QA/QC)",
            "args": {}
        },
    }
    
    def __init__(self, sources: List[str] = None):
        """
        Args:
            sources: 활성화할 소스 목록 (None이면 모두 활성화)
        """
        self.sources = sources
        self.results = []
        self.source_stats = {}
    
    def _get_days_back(self) -> int:
        """
        요일에 따른 수집 기간 결정
        - 월요일: 3일 (금~일 포함)
        - 그 외: 1일
        """
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return 3
        return 1
    
    def fetch_all(self, days_back: int = None) -> List[Dict[str, Any]]:
        """
        모든 활성화된 소스에서 뉴스 수집
        
        Args:
            days_back: 수집 기간 (None이면 자동 계산)
            
        Returns:
            통합된 뉴스 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        all_articles = []
        
        print("=" * 60)
        print("Multi-Source News Scraper")
        print("=" * 60)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Days back: {days_back}")
        print("=" * 60)
        
        for source_key, config in self.SCRAPERS_CONFIG.items():
            # 비활성화된 소스 건너뛰기
            if not config.get("enabled", True):
                continue
            
            # 특정 소스만 실행
            if self.sources and source_key not in self.sources:
                continue
            
            print(f"\n[{source_key.upper()}] {config['description']}")
            print("-" * 40)
            
            try:
                # 스크래퍼 인스턴스 생성
                scraper_class = config["class"]
                scraper_args = config.get("args", {})
                scraper = scraper_class(**scraper_args)
                
                # 뉴스 수집
                # 일부 소스는 자체 days_back 로직 사용 (FDA 등)
                if config.get("use_internal_days_back", False):
                    articles = scraper.fetch_news(days_back=None)
                else:
                    articles = scraper.fetch_news(days_back=days_back)
                
                # NewsArticle -> dict 변환 및 소스 표시
                for article in articles:
                    article_dict = article.to_dict() if hasattr(article, 'to_dict') else self._article_to_dict(article)
                    article_dict["scraper_source"] = source_key
                    all_articles.append(article_dict)
                
                print(f"[{source_key.upper()}] Collected: {len(articles)} articles")
                self.source_stats[config['description']] = len(articles)
                
            except Exception as e:
                print(f"[{source_key.upper()}] Error: {e}")
                import traceback
                traceback.print_exc()
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in all_articles:
            link = article.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                unique_articles.append(article)
        
        # 키워드/분류가 없는 기사 필터링
        filtered_articles = [
            a for a in unique_articles 
            if a.get("matched_keywords") or a.get("classifications")
        ]
        
        removed_count = len(unique_articles) - len(filtered_articles)
        if removed_count > 0:
            print(f"\n[FILTER] Removed {removed_count} articles without keywords/classifications")
        
        # 날짜순 정렬 (최신순)
        filtered_articles.sort(
            key=lambda x: x.get("published", "") or "",
            reverse=True
        )
        
        print("\n" + "=" * 60)
        print(f"TOTAL COLLECTED: {len(filtered_articles)} articles")
        print("=" * 60)
        
        self.results = filtered_articles
        return filtered_articles
    
    def _article_to_dict(self, article: NewsArticle) -> Dict[str, Any]:
        """NewsArticle을 딕셔너리로 변환"""
        return {
            "title": article.title,
            "link": article.link,
            "published": article.published.isoformat() if article.published else None,
            "source": article.source,
            "summary": article.summary,
            "classifications": article.classifications,
            "matched_keywords": article.matched_keywords,
        }
    
    def save_to_json(self, filepath: str = None) -> str:
        """
        결과를 JSON 파일로 저장
        
        Args:
            filepath: 저장 경로 (None이면 자동 생성)
            
        Returns:
            저장된 파일 경로
        """
        if not filepath:
            today = datetime.now().strftime('%Y%m%d')
            filepath = f"multi_source_news_{today}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n[SAVED] {filepath} ({len(self.results)} articles)")
        
        # 분류별 통계 계산
        classification_stats = {}
        for article in self.results:
            if "classifications" in article:
                for cls in article["classifications"]:
                    classification_stats[cls] = classification_stats.get(cls, 0) + 1
                    
        # 로그 기록
        logger.log_execution(
            total_articles=len(self.results),
            source_stats=self.source_stats,
            classification_stats=classification_stats,
            output_file=os.path.basename(filepath)
        )
        
        return filepath
    
    @classmethod
    def list_sources(cls):
        """사용 가능한 소스 목록 출력"""
        print("\nAvailable Sources:")
        print("-" * 40)
        for key, config in cls.SCRAPERS_CONFIG.items():
            status = "✓" if config.get("enabled", True) else "✗"
            print(f"  [{status}] {key}: {config['description']}")


# 독립 실행
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Source News Scraper")
    parser.add_argument("--sources", nargs="+", help="Specific sources to scrape")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: 1, Monday: 3)")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--list", action="store_true", help="List available sources")
    args = parser.parse_args()
    
    if args.list:
        MultiSourceScraper.list_sources()
    else:
        scraper = MultiSourceScraper(sources=args.sources)
        articles = scraper.fetch_all(days_back=args.days)
        
        if articles:
            output_path = scraper.save_to_json(args.output)
            print(f"\nNext steps:")
            print(f"  1. Run AI summarizer: python ai_summarizer.py -i {output_path}")
            print(f"  2. Send emails: python email_sender.py -i [summarized_file].json")
