# GMP Journal 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
import time
import re
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class GMPJournalScraper(BaseScraper):
    """
    GMP Journal 뉴스 스크래퍼
    URL: https://www.gmp-journal.com/search-result.html?p=query&keywords=
    English pharmaceutical/GMP regulatory news
    """
    
    @property
    def source_name(self) -> str:
        return "GMP Journal"
    
    @property
    def base_url(self) -> str:
        return "https://www.gmp-journal.com"
    
    @property
    def search_url(self) -> str:
        return f"{self.base_url}/search-result.html"
    
    def fetch_news(self, query: str = None, days_back: int = 7) -> List[NewsArticle]:
        """
        GMP Journal에서 뉴스 수집
        - query가 None이면 메인 페이지에서 최신 뉴스 수집
        - 기본 days_back을 7로 설정 (영문 사이트라 업데이트 빈도가 낮을 수 있음)
        """
        # query가 없으면 메인 페이지 수집
        if not query:
            url = self.base_url
            print(f"\n[PROCESS] {self.source_name}에서 최신 기사 수집")
        else:
            # 공백을 "+"로 대체
            encoded_query = query.replace(" ", "+")
            url = f"{self.search_url}?keywords={encoded_query}"
            print(f"\n[PROCESS] {self.source_name}에서 기사 수집, 검색어: '{query}'")
        
        articles = []
        page = 1
        max_pages = 3  # 최대 3페이지까지 수집
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        while page <= max_pages:
            page_url = f"{url}&page={page}" if page > 1 and query else url
            page_articles = self._fetch_page(page_url, cutoff_date)
            
            if not page_articles:
                break
            
            articles.extend(page_articles)
            page += 1
            time.sleep(1)  # 서버 부하 방지
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[SUCCESS] {len(unique_articles)}개의 뉴스를 수집했습니다.")
        return unique_articles
    
    def _fetch_page(self, url: str, cutoff_date: datetime) -> List[NewsArticle]:
        """단일 페이지에서 기사 수집"""
        soup = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    print(f"\n[WARNING] HTTP 오류: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                break
                
            except requests.exceptions.Timeout:
                print(f"\n[WARNING] 시간 초과 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"\n[ERROR] 최대 재시도 횟수 초과")
                    return []
            except Exception as e:
                print(f"\n[ERROR] 요청 실패: {e}")
                return []
        
        if soup is None:
            return []
        
        articles = []
        
        # 기사 목록 파싱 (div.even, div.odd - 번갈아가며 사용)
        article_items = soup.select('div.even, div.odd')
        
        for item in article_items:
            try:
                article = self._parse_article_item(item, cutoff_date)
                if article:
                    articles.append(article)
            except Exception as e:
                continue
        
        return articles
    
    # GMP Journal 본문 CSS 선택자
    CONTENT_SELECTORS = ['.article-body', '.content-body', 'article', '.main-content']
    
    def _parse_article_item(self, item, cutoff_date: datetime) -> NewsArticle | None:
        """개별 기사 아이템 파싱 + 본문 수집"""
        # 제목과 링크 (h3 > a)
        title_link = item.select_one('h3 > a')
        if not title_link:
            return None
        
        title = title_link.get_text(strip=True)
        href = title_link.get('href', '')
        
        if not title or not href:
            return None
        
        # 절대 URL 생성
        if href.startswith('/'):
            full_link = f"{self.base_url}{href}"
        elif not href.startswith('http'):
            full_link = f"{self.base_url}/{href}"
        else:
            full_link = href
        
        # 요약 (p.context)
        summary_elem = item.select_one('p.context')
        summary = summary_elem.get_text(strip=True) if summary_elem else ''
        
        # 날짜 파싱 (요약 텍스트에서 DD.MM.YYYY 형식 추출)
        published = self._extract_date_from_text(summary)
        
        # 날짜 필터링
        if published and published >= cutoff_date:
            classifications, matched_keywords = classify_article(title, summary)
            
            # 본문 수집
            content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)
            
            return NewsArticle(
                title=title,
                link=full_link,
                published=published,
                source=self.source_name,
                summary=summary,
                full_text=content.get("full_text", ""),
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )
        elif not published:
            # 날짜가 없는 경우에도 수집 (최근 기사일 가능성)
            classifications, matched_keywords = classify_article(title, summary)
            
            # 본문 수집
            content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)
            
            return NewsArticle(
                title=title,
                link=full_link,
                published=None,
                source=self.source_name,
                summary=summary,
                full_text=content.get("full_text", ""),
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )
        
        return None
    
    def _extract_date_from_text(self, text: str) -> datetime | None:
        """텍스트에서 날짜 추출 (DD.MM.YYYY 형식)"""
        if not text:
            return None
        
        # DD.MM.YYYY 형식 찾기
        date_pattern = r'(\d{2})\.(\d{2})\.(\d{4})'
        match = re.search(date_pattern, text)
        
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except ValueError:
                return None
        
        return None
    
    def _parse_date(self, date_text: str) -> datetime | None:
        """날짜 문자열 파싱"""
        if not date_text:
            return None
        
        formats = [
            "%d.%m.%Y",      # 30.10.2025
            "%Y-%m-%d",      # 2025-10-30
            "%d/%m/%Y",      # 30/10/2025
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        return None
