# MFDS RSS Scraper
# 식품의약품안전처 RSS 피드 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import time
import re
import sys
import os
from email.utils import parsedate_to_datetime

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class MFDSScraper(BaseScraper):
    """
    MFDS (식품의약품안전처) RSS 스크래퍼
    Korea Food and Drug Administration RSS 피드 수집
    
    다양한 카테고리의 뉴스/공지/규정 수집:
    - 보도자료, 공지, 공고
    - 행정처분, 법령자료
    - 안전성 서한, 위해정보
    """
    
    # RSS 피드 카테고리 정의
    RSS_FEEDS = {
        # 알림/공지
        "notice": {
            "name": "공지사항",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0003",
            "category": "알림"
        },
        "announcement": {
            "name": "공고",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0004",
            "category": "알림"
        },
        "admin_notice": {
            "name": "입법/행정예고",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0009",
            "category": "알림"
        },
        "public_service": {
            "name": "공시송달",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0013",
            "category": "알림"
        },
        
        # 지방식약청
        "local_busan": {
            "name": "부산청 공지",
            "url": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=2",
            "category": "지방청"
        },
        "local_gyeongin": {
            "name": "경인청 공지",
            "url": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=3",
            "category": "지방청"
        },
        "local_daegu": {
            "name": "대구청 공지",
            "url": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=4",
            "category": "지방청"
        },
        "local_gwangju": {
            "name": "광주청 공지",
            "url": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=5",
            "category": "지방청"
        },
        "local_daejeon": {
            "name": "대전청 공지",
            "url": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=6",
            "category": "지방청"
        },
        "local_seoul": {
            "name": "서울청 공지",
            "url": "https://mfds.go.kr/www/rss/brd.do?brdId=rgn0003&itm_seq_1=7",
            "category": "지방청"
        },

        # 언론홍보
        "press_release": {
            "name": "보도자료",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0021",
            "category": "언론홍보"
        },
        "press_explain": {
            "name": "언론보도 설명",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0022",
            "category": "언론홍보"
        },
        "card_news": {
            "name": "카드뉴스",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=card0001",
            "category": "언론홍보"
        },
        
        # 위해정보/행정처분
        "drug_sanction": {
            "name": "의약품 행정처분",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0117",
            "category": "행정처분"
        },
        "device_sanction": {
            "name": "의료기기 행정처분",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0168",
            "category": "행정처분"
        },
        "bio_sanction": {
            "name": "바이오 행정처분",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0138",
            "category": "행정처분"
        },
        "test_lab_sanction": {
            "name": "시험검사기관 행정처분",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0039",
            "category": "행정처분"
        },
        "device_recall": {
            "name": "의료기기 회수/판매중지",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0139",
            "category": "위해정보"
        },
         "foreign_drug_risk": {
            "name": "외국 위해의약품",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0018",
            "category": "위해정보"
        },
        "safety_letter": {
            "name": "안전성 서한",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=seohan001",
            "category": "위해정보"
        },
        
        # 법령자료
        "recent_laws": {
            "name": "제개정고시등",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0008",
            "category": "법령"
        },
        "notification": {
            "name": "고시전문",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0005",
            "category": "법령"
        },
        "directive": {
            "name": "훈령전문",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0006",
            "category": "법령"
        },
        "regulation": {
            "name": "예규전문",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0007",
            "category": "법령"
        },
        "law_status": {
            "name": "법률 제·개정 현황",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=relaw0001",
            "category": "법령"
        },
        "law_decree": {
            "name": "법, 시행령, 시행규칙",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0003",
            "category": "법령"
        },
         "foreign_law": {
            "name": "식의약품 국외법령자료",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=food0001",
            "category": "법령"
        },
        
        # 가이드/지침
        "civil_guide": {
            "name": "민원인안내서",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0011",
            "category": "가이드"
        },
        "guideline": {
            "name": "안내서/지침",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0013",
            "category": "가이드"
        },
        "official_guide": {
            "name": "공무원지침서",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0010",
            "category": "가이드"
        },
        
        # 기술/교육
        "test_method": {
            "name": "시험법공유",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=plc0065",
            "category": "기술"
        },
         "discussion": {
            "name": "학술 토론회",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0014",
            "category": "기술"
        },
        
        # 기타 리소스
        "forms": {
            "name": "민원서식",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0015",
            "category": "자료"
        },
        "edu_materials": {
            "name": "교육홍보물",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0019",
            "category": "자료"
        },
        "special_materials": {
            "name": "전문홍보물",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0020",
            "category": "자료"
        },
        "video_materials": {
            "name": "동영상홍보물",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0021",
            "category": "자료"
        },
        "general_materials": {
            "name": "일반홍보물",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=data0018",
            "category": "자료"
        },
        "personnel": {
            "name": "인사동정",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0087",
            "category": "기관소식"
        },
        "ntc0056": {
            "name": "기타공지1",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0056",
            "category": "기타"
        },
        "ntc0063": {
            "name": "기타공지2",
            "url": "http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0063",
            "category": "기타"
        }
    }
    
    # 주요 피드 그룹
    FEED_GROUPS = {
        "main": ["notice", "announcement", "admin_notice", "press_release"],
        "safety": ["drug_sanction", "foreign_drug_risk", "device_sanction", "device_recall", "bio_sanction", "safety_letter", "test_lab_sanction"],
        "local": ["local_busan", "local_gyeongin", "local_daegu", "local_gwangju", "local_daejeon", "local_seoul"],
        "regulation": ["recent_laws", "notification", "directive", "regulation", "law_status", "law_decree", "foreign_law"],
        "guide": ["civil_guide", "guideline", "official_guide", "test_method"],
        "materials": ["forms", "edu_materials", "special_materials", "video_materials", "general_materials", "card_news"],
        "all": list(RSS_FEEDS.keys())
    }
    
    def __init__(self, feeds: str = "main"):
        """
        MFDS 스크래퍼 초기화
        
        Args:
            feeds: 수집할 피드 그룹 ("main", "safety", "regulation", "guide", "all")
                   또는 개별 피드 키 (쉼표로 구분)
        """
        self.selected_feeds = self._resolve_feeds(feeds)
    
    def _resolve_feeds(self, feeds: str) -> List[str]:
        """피드 선택 해석"""
        feeds = feeds.lower().strip()
        
        if feeds in self.FEED_GROUPS:
            return self.FEED_GROUPS[feeds]
        
        # 쉼표로 구분된 개별 피드
        keys = [f.strip() for f in feeds.split(",")]
        return [k for k in keys if k in self.RSS_FEEDS]
    
    @property
    def source_name(self) -> str:
        return "MFDS (식품의약품안전처)"
    
    @property
    def base_url(self) -> str:
        return "https://www.mfds.go.kr"
    
    def get_headers(self) -> dict:
        """HTTP 요청 헤더"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    def fetch_news(self, query: str = None, days_back: int = 7) -> List[NewsArticle]:
        """
        MFDS RSS 피드에서 뉴스 수집
        
        Args:
            query: 검색 키워드 (선택적)
            days_back: 수집할 기간 (일수)
            
        Returns:
            NewsArticle 리스트
        """
        all_articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for feed_key in self.selected_feeds:
            if feed_key not in self.RSS_FEEDS:
                continue
            
            feed_info = self.RSS_FEEDS[feed_key]
            
            try:
                print(f"[MFDS] Fetching: {feed_info['name']} ({feed_key})")
                
                articles = self._fetch_rss_feed(
                    feed_info["url"],
                    feed_info["name"],
                    feed_info["category"],
                    cutoff_date,
                    query
                )
                
                all_articles.extend(articles)
                print(f"[MFDS] Found {len(articles)} items in {feed_info['name']}")
                
                # Rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                print(f"[MFDS] Error fetching {feed_key}: {e}")
        
        # 날짜순 정렬 (최신순)
        all_articles.sort(key=lambda x: x.published if x.published else datetime.min, reverse=True)
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in all_articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[MFDS] Total collected: {len(unique_articles)} articles")
        return unique_articles
    
    def _fetch_rss_feed(self, url: str, feed_name: str, category: str, 
                        cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """개별 RSS 피드 파싱"""
        articles = []
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # XML 파싱
            soup = BeautifulSoup(response.text, 'xml')
            
            items = soup.find_all('item')
            
            for item in items:
                article = self._parse_rss_item(item, feed_name, category, cutoff_date, query)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            print(f"[MFDS] Error parsing RSS {url}: {e}")
        
        return articles
    
    # MFDS 본문 CSS 선택자
    CONTENT_SELECTORS = ['.view_cont', '.bbs_view', '.board_view', '#contents', '.content_area']
    
    def _parse_rss_item(self, item, feed_name: str, category: str, 
                        cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """RSS 아이템 파싱 + 본문 수집"""
        try:
            # 제목
            title_elem = item.find('title')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                return None
            
            # 링크
            link_elem = item.find('link')
            link = link_elem.get_text(strip=True) if link_elem else None
            
            if not link:
                return None
            
            # 날짜 파싱
            pub_date_elem = item.find('pubDate')
            published = None
            if pub_date_elem:
                pub_date_str = pub_date_elem.get_text(strip=True)
                published = self._parse_rss_date(pub_date_str)
            
            # 날짜 필터링
            if published and published < cutoff_date:
                return None
            
            # 키워드 필터링
            if query and query.lower() not in title.lower():
                return None
            
            # 내용/요약 (RSS에서)
            content_elem = item.find('content:encoded') or item.find('description')
            summary = content_elem.get_text(strip=True)[:500] if content_elem else ""
            
            # 분류 수행
            classifications, matched_keywords = classify_article(title, summary)
            
            # 기본 분류 추가
            if not classifications:
                classifications = [category]
                matched_keywords = ["MFDS", feed_name]
            
            # 본문 수집 (링크에서 전체 내용)
            content = self.fetch_article_content(link, self.CONTENT_SELECTORS)
            
            return NewsArticle(
                title=title,
                link=link,
                published=published,
                source=f"MFDS-{feed_name}",
                summary=summary if summary else f"Source: MFDS {feed_name}",
                full_text=content.get("full_text", ""),
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )
            
        except Exception as e:
            return None
    
    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """RSS 날짜 파싱"""
        if not date_str:
            return None
        
        try:
            # RFC 2822 형식 (Tue, 06 Jan 2026 00:04:43 GMT)
            dt = parsedate_to_datetime(date_str)
            return dt.replace(tzinfo=None)  # naive datetime으로 변환
        except Exception:
            pass
        
        # 대체 형식 시도
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    @classmethod
    def list_available_feeds(cls) -> None:
        """사용 가능한 피드 목록 출력"""
        print("\n" + "=" * 60)
        print("MFDS RSS Feeds Available")
        print("=" * 60)
        
        categories = {}
        for key, info in cls.RSS_FEEDS.items():
            cat = info["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((key, info["name"]))
        
        for cat, feeds in categories.items():
            print(f"\n{cat}:")
            for key, name in feeds:
                print(f"  - {key}: {name}")
        
        print("\n" + "-" * 40)
        print("Feed Groups:")
        for group, keys in cls.FEED_GROUPS.items():
            print(f"  - {group}: {len(keys)} feeds")


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MFDS RSS Scraper")
    parser.add_argument("--feeds", default="main",
                       help="Feeds to scrape: main, safety, regulation, guide, all")
    parser.add_argument("--days", type=int, default=7,
                       help="Days back to scrape")
    parser.add_argument("--list", action="store_true",
                       help="List available feeds")
    args = parser.parse_args()
    
    if args.list:
        MFDSScraper.list_available_feeds()
    else:
        scraper = MFDSScraper(feeds=args.feeds)
        
        print("=" * 60)
        print(f"MFDS RSS Scraper - {args.feeds}")
        print("=" * 60)
        
        articles = scraper.fetch_news(days_back=args.days)
        
        print(f"\nTotal collected: {len(articles)} articles\n")
        
        for i, article in enumerate(articles[:15], 1):
            date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
            print(f"{i}. [{date_str}] {article.title[:60]}...")
            print(f"   Source: {article.source}")
            print(f"   Link: {article.link}")
            print()
