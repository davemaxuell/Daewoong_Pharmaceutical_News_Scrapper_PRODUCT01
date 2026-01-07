# EudraLex Volume 4 스크래퍼
# EU GMP Guidelines (EU 의약품 제조 및 품질관리 기준) 업데이트 모니터링

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


class EudraLexScraper(BaseScraper):
    """
    EudraLex Volume 4 스크래퍼
    EU GMP Guidelines 업데이트 모니터링
    
    EudraLex Volume 4는 EU 의약품 GMP 가이드라인을 담고 있으며,
    Part I-IV, Annexes 1-21 등 제조 및 품질관리 기준을 포함
    """
    
    @property
    def source_name(self) -> str:
        return "EudraLex"
    
    @property
    def base_url(self) -> str:
        return "https://health.ec.europa.eu"
    
    @property
    def page_url(self) -> str:
        return f"{self.base_url}/medicinal-products/eudralex/eudralex-volume-4_en"
    
    def fetch_news(self, query: str = None, days_back: int = 1) -> List[NewsArticle]:
        """
        EudraLex 최신 업데이트 수집
        
        Args:
            query: 검색 키워드 (선택적, 제목/요약 필터링용)
            days_back: 수집할 기간 (일수)
            
        Returns:
            NewsArticle 리스트
        """
        print(f"\n[PROCESS] {self.source_name}에서 최신 업데이트 수집 중...")
        
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(self.page_url, headers=self.get_headers(), timeout=30)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    print(f"[WARNING] HTTP 오류: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Latest Updates 섹션에서 기사 카드 찾기
                # ECL (Europa Component Library) 구조 사용
                cards = soup.select('article.ecl-card')
                
                for card in cards:
                    article = self._parse_card(card, cutoff_date, query)
                    if article:
                        articles.append(article)
                
                break  # 성공하면 루프 종료
                
            except requests.exceptions.Timeout:
                print(f"[WARNING] 시간 초과 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"[ERROR] 최대 재시도 횟수 초과")
                    return []
            except Exception as e:
                print(f"[ERROR] 요청 실패: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return []
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[SUCCESS] {len(unique_articles)}개의 EudraLex 업데이트를 수집했습니다.")
        return unique_articles
    
    # EudraLex 본문 CSS 선택자
    CONTENT_SELECTORS = ['.ecl-body', '.ecl-paragraph', 'article', '.main-content']
    
    def _parse_card(self, card, cutoff_date: datetime, query: str = None) -> NewsArticle | None:
        """개별 카드 파싱 + 본문 수집"""
        try:
            # 제목과 링크 (.ecl-content-block__title a)
            title_elem = card.select_one('.ecl-content-block__title a')
            if not title_elem:
                # 대체 선택자 시도
                title_elem = card.select_one('a[href]')
            
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
            
            # 날짜 파싱 (time 요소)
            time_elem = card.select_one('time')
            published = None
            if time_elem:
                # datetime 속성 우선 사용
                datetime_attr = time_elem.get('datetime', '')
                if datetime_attr:
                    published = self._parse_datetime(datetime_attr)
                else:
                    # 텍스트에서 날짜 추출
                    date_text = time_elem.get_text(strip=True)
                    published = self._parse_date_text(date_text)
            
            # 날짜가 없는 항목은 건너뜀 (네비게이션 링크 등)
            if not published:
                return None
            
            # 날짜 필터링
            if published < cutoff_date:
                return None
            
            # 요약/설명 찾기
            summary_elem = card.select_one('.ecl-content-block__description')
            summary = summary_elem.get_text(strip=True) if summary_elem else ''
            
            # 카테고리/타입 확인
            type_elem = card.select_one('.ecl-content-block__primary-meta-container')
            content_type = type_elem.get_text(strip=True) if type_elem else ''
            
            # 키워드 필터링 (선택적)
            if query:
                query_lower = query.lower()
                if query_lower not in title.lower() and query_lower not in summary.lower():
                    return None
            
            # 키워드 분류
            classifications, matched_keywords = classify_article(title, summary)
            
            # EudraLex 기본 분류 추가
            if not classifications:
                classifications = ["규제행정"]
                matched_keywords = ["EudraLex", "EU GMP"]
            
            # 본문 수집
            content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)
            
            return NewsArticle(
                title=title,
                link=full_link,
                published=published,
                source=self.source_name,
                summary=summary[:500] if summary else content_type,
                full_text=content.get("full_text", ""),
                images=content.get("images", []),
                scrape_status=content.get("status", "pending"),
                classifications=classifications,
                matched_keywords=matched_keywords
            )
            
        except Exception as e:
            print(f"[DEBUG] 카드 파싱 실패: {e}")
            return None
    
    def _parse_datetime(self, datetime_str: str) -> datetime | None:
        """ISO 형식 datetime 파싱"""
        if not datetime_str:
            return None
        
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",      # 2025-12-18T12:00:00Z
            "%Y-%m-%dT%H:%M:%S%z",     # 2025-12-18T12:00:00+00:00
            "%Y-%m-%dT%H:%M:%S",       # 2025-12-18T12:00:00
            "%Y-%m-%d",                 # 2025-12-18
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str.strip(), fmt)
                # timezone-aware를 naive로 변환
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except ValueError:
                continue
        
        return None
    
    def _parse_date_text(self, date_text: str) -> datetime | None:
        """텍스트 날짜 파싱 (예: "18 December 2025")"""
        if not date_text:
            return None
        
        formats = [
            "%d %B %Y",      # 18 December 2025
            "%d %b %Y",      # 18 Dec 2025
            "%B %d, %Y",     # December 18, 2025
            "%Y-%m-%d",      # 2025-12-18
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        
        return None
