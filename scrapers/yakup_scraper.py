# 약업신문 (Yakup) 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List
import time
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class YakupScraper(BaseScraper):
    """
    약업신문 (Yakup) 뉴스 스크래퍼
    URL: https://www.yakup.com/search/index.html?csearch_word=검색어&csearch_type=news
    """
    
    @property
    def source_name(self) -> str:
        return "Yakup"
    
    @property
    def base_url(self) -> str:
        return "https://www.yakup.com"
    
    def _get_search_url(self, query: str) -> str:
        """검색 URL 생성 (뉴스 타입으로 필터)"""
        # 공백을 "+"로 대체
        encoded_query = query.replace(" ", "+")
        return f"{self.base_url}/search/index.html?csearch_word={encoded_query}&csearch_type=news"
    
    def fetch_news(self, query: str = "제약", days_back: int = 1) -> List[NewsArticle]:
        """
        약업신문에서 뉴스 수집
        - 공백은 "+"로 대체
        - 뉴스 타입으로 필터링
        - query 기본값: "제약" (multi-source 호환)
        """
        url = self._get_search_url(query)
        
        print(f"\n[PROCESS] {self.source_name}에서 기사 수집, 검색어: '{query}'")
        
        # 재시도 로직 (최대 3회)
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
                    print(f"\n[ERROR] 최대 재시도 횟수 초과: {query}")
                    return []
            except Exception as e:
                print(f"\n[ERROR] 요청 실패: {e}")
                return []
        
        if soup is None:
            return []
        
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # 기사 목록 파싱 - mode=view 포함하는 링크
        article_links = soup.select('a[href*="mode=view"]')
        
        for link_tag in article_links:
            try:
                article = self._parse_article_item(link_tag, cutoff_date)
                if article:
                    articles.append(article)
            except Exception as e:
                continue
        
        print(f"[SUCCESS] {len(articles)}개의 뉴스를 수집했습니다.")
        return articles
    
    # Yakup 본문 CSS 선택자
    CONTENT_SELECTORS = ['.article_body', '.view_cont', '.news_body', '#articleBody']
    
    def _parse_article_item(self, link_tag, cutoff_date: datetime) -> NewsArticle | None:
        """개별 기사 아이템 파싱 + 본문 수집"""
        href = link_tag.get('href', '')
        
        # 절대 URL 생성
        if href.startswith('/'):
            full_link = f"{self.base_url}{href}"
        else:
            full_link = href
        
        # 제목 (.title_con span)
        title_elem = link_tag.select_one('.title_con span')
        title = title_elem.get_text(strip=True) if title_elem else ''
        
        if not title:
            return None
        
        # 요약 (.text_con span)
        summary_elem = link_tag.select_one('.text_con span')
        summary = summary_elem.get_text(strip=True) if summary_elem else ''
        
        # 날짜 (.name_con span) - Format: YYYY-MM-DD HH:MM
        date_elem = link_tag.select_one('.name_con span')
        date_text = date_elem.get_text(strip=True) if date_elem else ''
        
        # 날짜 파싱
        published = self._parse_date(date_text)
        
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
            # 날짜가 없는 경우에도 수집
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
    
    def _parse_date(self, date_text: str) -> datetime | None:
        """날짜 문자열 파싱"""
        if not date_text:
            return None
        
        formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        return None
