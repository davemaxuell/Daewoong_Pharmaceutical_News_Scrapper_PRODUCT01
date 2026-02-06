# EDQM Newsroom Scraper
# European Directorate for the Quality of Medicines & HealthCare 뉴스룸 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import time
import re
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class EDQMScraper(BaseScraper):
    """
    EDQM Newsroom Scraper
    European Directorate for the Quality of Medicines & HealthCare 뉴스 수집
    
    지원하는 뉴스룸:
    - CEP (Certification of Suitability)
    - Pharmaceuticals (Classification of Medicines)
    - OMCL (Official Medicines Control Laboratories)
    - Pharmaceutical Care
    - Nitrosamine
    - Anti-Falsification
    """
    
    # 지원하는 뉴스룸 URL 목록
    NEWSROOMS = {
        "pheur": "https://www.edqm.eu/en/newsroom-pheur",
        "cep": "https://www.edqm.eu/en/newsroom-cep",
        "pharmaceuticals": "https://www.edqm.eu/en/newsroom-pharmaceuticals",
        "omcl": "https://www.edqm.eu/en/omcl-newsroom",
        "pharmaceutical-care": "https://www.edqm.eu/en/pharmaceutical-care-newsroom",
        "nitrosamine": "https://www.edqm.eu/en/newsroom-nitrosamine",
        "anti-falsification": "https://www.edqm.eu/en/newsroom-anti-falsification",
    }
    
    def __init__(self, newsroom: str = "all"):
        """
        EDQM 스크래퍼 초기화
        
        Args:
            newsroom: 수집할 뉴스룸 ("cep", "pharmaceuticals", "omcl", 
                      "pharmaceutical-care", "nitrosamine", "anti-falsification", 
                      또는 "all"로 모두 수집)
        """
        self.newsroom = newsroom.lower()
    
    @property
    def source_name(self) -> str:
        if self.newsroom == "all":
            return "EDQM Newsrooms"
        return f"EDQM {self.newsroom.upper()}"
    
    @property
    def base_url(self) -> str:
        return "https://www.edqm.eu"
    
    def get_newsroom_urls(self) -> List[tuple]:
        """
        수집할 뉴스룸 URL 목록 반환
        
        Returns:
            (이름, URL) 튜플 리스트
        """
        if self.newsroom == "all":
            return list(self.NEWSROOMS.items())
        elif self.newsroom in self.NEWSROOMS:
            return [(self.newsroom, self.NEWSROOMS[self.newsroom])]
        else:
            print(f"[EDQM] Unknown newsroom: {self.newsroom}")
            print(f"[EDQM] Available: {', '.join(self.NEWSROOMS.keys())}, all")
            return []
    
    def _get_days_back(self) -> int:
        """
        수집 기간 결정
        EDQM은 자주 게시하지 않으므로 7일 기본값 사용
        (중복 제거는 AI 시스템에서 처리)
        """
        return 7  # EDQM publishes infrequently, use 7 days
    
    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        EDQM 뉴스룸에서 최신 뉴스 수집
        
        Args:
            query: 검색 키워드 (선택적, 제목 필터링용)
            days_back: 수집할 기간 (None이면 자동 - 1일, 월요일은 3일)
            
        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        all_articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        newsroom_urls = self.get_newsroom_urls()
        
        print(f"[EDQM] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        if not newsroom_urls:
            return []
        
        for name, url in newsroom_urls:
            try:
                print(f"[EDQM] Fetching from: {name} ({url})")
                
                response = requests.get(
                    url,
                    headers=self.get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 뉴스 아이템 컨테이너 찾기
                news_items = soup.select('div.element.itemCat')
                
                print(f"[EDQM] Found {len(news_items)} items in {name}")
                
                for item in news_items:
                    try:
                        article = self._parse_news_item(item, cutoff_date, query, name)
                        if article:
                            all_articles.append(article)
                    except Exception as e:
                        print(f"[EDQM] Error parsing item: {e}")
                        continue
                
                # Rate limiting
                if len(newsroom_urls) > 1:
                    time.sleep(0.5)
                    
            except requests.RequestException as e:
                print(f"[EDQM] Request error for {name}: {e}")
            except Exception as e:
                print(f"[EDQM] Unexpected error for {name}: {e}")
        
        # 날짜순 정렬 (최신순)
        all_articles.sort(key=lambda x: x.published if x.published else datetime.min, reverse=True)
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in all_articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[EDQM] Successfully collected {len(unique_articles)} articles")
        return unique_articles
    
    # EDQM 본문 CSS 선택자
    CONTENT_SELECTORS = ['.node__content', '.field--name-body', 'article', '.main-content']
    
    def _parse_news_item(self, item, cutoff_date: datetime, query: str = None, newsroom_name: str = "") -> Optional[NewsArticle]:
        """
        뉴스 아이템 파싱 + 본문 수집
        
        Args:
            item: BeautifulSoup element
            cutoff_date: 필터링할 기준 날짜
            query: 검색 키워드 (선택적)
            newsroom_name: 뉴스룸 이름
            
        Returns:
            NewsArticle 또는 None
        """
        # 제목과 링크 추출 (h3 a 태그)
        title_elem = item.select_one('h3 a')
        if not title_elem:
            # 대체 선택자
            title_elem = item.select_one('a')
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        href = title_elem.get('href', '')
        
        if not title or not href:
            return None
        
        # 절대 URL 생성
        if href.startswith('/'):
            full_link = f"{self.base_url}{href}"
        elif not href.startswith('http'):
            full_link = f"{self.base_url}/{href}"
        else:
            full_link = href
        
        # 날짜 추출 (.upper span.date 또는 텍스트에서)
        date_elem = item.select_one('.upper span.date')
        if not date_elem:
            date_elem = item.select_one('span.date')
        
        published = None
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            published = self._parse_date(date_text)
        else:
            # item 텍스트에서 날짜 패턴 찾기
            item_text = item.get_text()
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', item_text)
            if date_match:
                published = self._parse_date(date_match.group(1))
        
        # 날짜 필터링
        if published and published < cutoff_date:
            return None
        
        # 키워드 필터링
        if query and query.lower() not in title.lower():
            return None
        
        # 요약 추출
        summary_elem = item.select_one('p')
        summary = summary_elem.get_text(strip=True) if summary_elem else ""
        
        # 분류 수행
        classifications, matched_keywords = classify_article(title, summary)
        
        # EDQM 기본 분류 추가
        if not classifications:
            classifications = ["규제행정"]
            matched_keywords = ["EDQM", newsroom_name]
        
        # 본문 수집
        content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)
        
        return NewsArticle(
            title=title,
            link=full_link,
            published=published,
            source=f"EDQM {newsroom_name.upper()}",
            summary=summary[:500] if summary else f"Source: EDQM {newsroom_name}",
            full_text=content.get("full_text", ""),
            images=content.get("images", []),
            scrape_status=content.get("status", "pending"),
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        날짜 파싱 (DD/MM/YYYY 형식)
        
        Args:
            date_text: 파싱할 날짜 텍스트
            
        Returns:
            datetime 또는 None
        """
        if not date_text:
            return None
        
        # DD/MM/YYYY 형식
        formats = [
            "%d/%m/%Y",      # 08/12/2025
            "%d-%m-%Y",      # 08-12-2025
            "%Y-%m-%d",      # 2025-12-08
            "%d %B %Y",      # 08 December 2025
            "%d %b %Y",      # 08 Dec 2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        
        return None


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EDQM Newsroom Scraper")
    parser.add_argument("--newsroom", default="all",
                       help="Newsroom to scrape (cep, pharmaceuticals, omcl, pharmaceutical-care, nitrosamine, anti-falsification, or 'all')")
    parser.add_argument("--days", type=int, default=30,
                       help="Days back to scrape")
    args = parser.parse_args()
    
    scraper = EDQMScraper(newsroom=args.newsroom)
    
    print("=" * 60)
    print(f"EDQM Scraper - {scraper.source_name}")
    print("=" * 60)
    
    articles = scraper.fetch_news(days_back=args.days)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:15], 1):
        print(f"{i}. {article.title[:70]}...")
        print(f"   Date: {article.published}")
        print(f"   Source: {article.source}")
        print(f"   Link: {article.link}")
        print()
