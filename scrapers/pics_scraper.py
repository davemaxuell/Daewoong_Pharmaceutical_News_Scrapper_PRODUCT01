# PIC/S News Scraper
# Pharmaceutical Inspection Co-operation Scheme 뉴스 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import re
import sys
import os
from email.utils import parsedate_to_datetime

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class PICSScraper(BaseScraper):
    """
    PIC/S (Pharmaceutical Inspection Co-operation Scheme) 뉴스 스크래퍼
    
    RSS 피드와 웹페이지 두 가지 방식 지원:
    - RSS: https://picscheme.org/rss/general_en.rss
    - Web: https://picscheme.org/en/news
    """
    
    RSS_URL = "https://picscheme.org/rss/general_en.rss"
    WEB_URL = "https://picscheme.org/en/news"
    
    @property
    def source_name(self) -> str:
        return "PIC/S"
    
    @property
    def base_url(self) -> str:
        return "https://picscheme.org"
    
    def _get_days_back(self) -> int:
        """
        요일에 따른 수집 기간 결정
        - 금요일: 3일 (수~금 포함)
        - 그 외: 1일
        """
        today = datetime.now()
        if today.weekday() == 4:  # Friday
            return 3
        return 1
    
    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        PIC/S 뉴스 수집 (RSS 피드 우선, 실패시 웹 스크래핑)
        
        Args:
            query: 검색 키워드 (선택적)
            days_back: 수집 기간 (None이면 자동 계산)
            
        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        print(f"[PIC/S] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        
        # RSS 피드 시도
        articles = self._fetch_from_rss(cutoff_date, query)
        
        if not articles:
            # RSS 실패시 웹 스크래핑
            print("[PIC/S] RSS failed, trying web scraping...")
            articles = self._fetch_from_web(cutoff_date, query)
        
        print(f"[PIC/S] Collected: {len(articles)} articles")
        return articles
    
    def _fetch_from_rss(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """RSS 피드에서 뉴스 수집"""
        articles = []
        
        try:
            print(f"[PIC/S] Fetching RSS: {self.RSS_URL}")
            
            response = requests.get(self.RSS_URL, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')
            
            print(f"[PIC/S] Found {len(items)} RSS items")
            
            for item in items:
                article = self._parse_rss_item(item, cutoff_date, query)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            print(f"[PIC/S] RSS error: {e}")
        
        return articles
    
    # PICS 본문 CSS 선택자
    CONTENT_SELECTORS = ['article', '.news-content', '.main-content', '#content']
    
    def _parse_rss_item(self, item, cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
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
            
            # 날짜
            pub_date_elem = item.find('pubDate')
            published = None
            if pub_date_elem:
                try:
                    published = parsedate_to_datetime(pub_date_elem.get_text(strip=True))
                    published = published.replace(tzinfo=None)
                except:
                    pass
            
            # 날짜 필터링
            if published and published < cutoff_date:
                return None
            
            # 키워드 필터링
            if query and query.lower() not in title.lower():
                return None
            
            # 설명/요약
            desc_elem = item.find('description')
            summary = desc_elem.get_text(strip=True)[:500] if desc_elem else ""
            
            # 분류
            classifications, matched_keywords = classify_article(title, summary)
            if not classifications:
                classifications = ["GMP", "규제"]
                matched_keywords = ["PIC/S", "GMP"]
            
            # 본문 수집
            content = self.fetch_article_content(link, self.CONTENT_SELECTORS)
            
            return NewsArticle(
                title=title,
                link=link,
                published=published,
                source=self.source_name,
                summary=summary,
                full_text=content.get("full_text", ""),
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )
            
        except Exception as e:
            return None
    
    def _fetch_from_web(self, cutoff_date: datetime, query: str = None) -> List[NewsArticle]:
        """웹 페이지에서 뉴스 수집"""
        articles = []
        
        try:
            print(f"[PIC/S] Fetching web: {self.WEB_URL}")
            
            response = requests.get(self.WEB_URL, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 월/년 레이블과 제목 찾기
            date_labels = soup.select('span.date_listing')
            titles = soup.select('h2')
            
            print(f"[PIC/S] Found {len(titles)} news titles")
            
            current_month_year = None
            
            for title_elem in titles:
                # 이전 형제에서 날짜 레이블 찾기
                prev = title_elem.find_previous('span', class_='date_listing')
                if prev:
                    current_month_year = prev.get_text(strip=True)
                
                title = title_elem.get_text(strip=True)
                if not title:
                    continue
                
                # 링크 (h2 내부 또는 h2 자체)
                link_elem = title_elem.find('a')
                if link_elem:
                    link = link_elem.get('href', '')
                    if link and not link.startswith('http'):
                        link = self.base_url + link
                else:
                    link = self.WEB_URL
                
                # 날짜 파싱 (월/년에서)
                published = self._parse_month_year(current_month_year) if current_month_year else None
                
                # 본문에서 정확한 날짜 찾기 시도
                next_p = title_elem.find_next('p')
                if next_p:
                    p_text = next_p.get_text(strip=True)
                    exact_date = self._extract_date_from_text(p_text)
                    if exact_date:
                        published = exact_date
                
                # 날짜 필터링
                if published and published < cutoff_date:
                    continue
                
                # 키워드 필터링
                if query and query.lower() not in title.lower():
                    continue
                
                # 요약 (다음 p 태그)
                summary = next_p.get_text(strip=True)[:300] if next_p else ""
                
                # 분류
                classifications, matched_keywords = classify_article(title, summary)
                if not classifications:
                    classifications = ["GMP", "규제"]
                    matched_keywords = ["PIC/S", "GMP"]
                
                # 본문 수집
                content = self.fetch_article_content(link, self.CONTENT_SELECTORS)
                
                articles.append(NewsArticle(
                    title=title,
                    link=link,
                    published=published,
                    source=self.source_name,
                    summary=summary,
                    full_text=content.get("full_text", ""),
                    images=content.get("images", []),
                    scrape_status=content.get("status", "pending"),
                    classifications=classifications,
                    matched_keywords=matched_keywords
                ))
                
        except Exception as e:
            print(f"[PIC/S] Web scraping error: {e}")
        
        return articles
    
    def _parse_month_year(self, text: str) -> Optional[datetime]:
        """월/년 텍스트 파싱 (예: 'January 2026')"""
        if not text:
            return None
        
        try:
            return datetime.strptime(text.strip(), "%B %Y")
        except ValueError:
            pass
        
        return None
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """텍스트에서 날짜 추출 (예: 'Geneva, 1 January 2026:')"""
        if not text:
            return None
        
        # 패턴: "1 January 2026" 또는 "15 December 2025"
        patterns = [
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    day = int(match.group(1))
                    month = match.group(2)
                    year = int(match.group(3))
                    return datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                except ValueError:
                    pass
        
        return None


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PIC/S News Scraper")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 1 day or 3 on Monday)")
    args = parser.parse_args()
    
    scraper = PICSScraper()
    
    print("=" * 60)
    print("PIC/S News Scraper")
    print("=" * 60)
    
    articles = scraper.fetch_news(days_back=args.days)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:60]}...")
        print(f"   Link: {article.link}")
        print()
