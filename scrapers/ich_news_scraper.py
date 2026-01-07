# ICH (International Council for Harmonisation) 뉴스 스크래퍼
# RSS 피드 기반으로 규제 가이드라인 및 업데이트 모니터링

import feedparser
from datetime import datetime, timedelta
from typing import List
import time
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class ICHScraper(BaseScraper):
    """
    ICH (International Council for Harmonisation) 뉴스 스크래퍼
    RSS 피드를 사용하여 규제 가이드라인 업데이트 모니터링
    
    ICH는 의약품 규제 가이드라인(Q1-Q14, M1-M13, S1-S12, E1-E19 등)을 
    발행하는 국제기구로, FDA, EMA, PMDA 등 주요 규제기관이 참여
    """
    
    @property
    def source_name(self) -> str:
        return "ICH"
    
    @property
    def base_url(self) -> str:
        return "https://www.ich.org"
    
    @property
    def rss_url(self) -> str:
        return "https://admin.ich.org/rss/news"
    
    def fetch_news(self, query: str = None, days_back: int = 7) -> List[NewsArticle]:
        """
        ICH RSS 피드에서 뉴스 수집
        
        Args:
            query: 검색 키워드 (RSS에서는 필터링용으로 사용, 선택적)
            days_back: 수집할 기간 (일수), 기본 7일
            
        Returns:
            NewsArticle 리스트
        """
        print(f"\n[PROCESS] {self.source_name} RSS 피드에서 뉴스 수집 중...")
        
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # RSS 피드 파싱
                feed = feedparser.parse(self.rss_url)
                
                if feed.bozo and feed.bozo_exception:
                    print(f"[WARNING] RSS 파싱 경고: {feed.bozo_exception}")
                
                if not feed.entries:
                    print(f"[WARNING] RSS 피드에서 항목을 찾을 수 없습니다.")
                    return []
                
                for entry in feed.entries:
                    article = self._parse_rss_entry(entry, cutoff_date, query)
                    if article:
                        articles.append(article)
                
                break  # 성공하면 루프 종료
                
            except Exception as e:
                print(f"[WARNING] RSS 수집 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"[ERROR] 최대 재시도 횟수 초과")
                    return []
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[SUCCESS] {len(unique_articles)}개의 ICH 뉴스를 수집했습니다.")
        return unique_articles
    
    def _parse_rss_entry(self, entry, cutoff_date: datetime, query: str = None) -> NewsArticle | None:
        """
        RSS 엔트리를 NewsArticle로 변환
        
        Args:
            entry: feedparser의 RSS 엔트리
            cutoff_date: 수집 기준일
            query: 필터링할 키워드 (선택적)
        """
        try:
            # 제목
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # 링크
            link = entry.get('link', '')
            if not link:
                return None
            
            # 절대 URL 확인
            if link.startswith('/'):
                link = f"{self.base_url}{link}"
            
            # 요약/설명
            summary = entry.get('summary', '') or entry.get('description', '')
            summary = summary.strip()
            
            # 날짜 파싱
            published = self._parse_date(entry)
            
            # 날짜 필터링
            if published and published < cutoff_date:
                return None
            
            # 키워드 필터링 (선택적)
            if query:
                query_lower = query.lower()
                if query_lower not in title.lower() and query_lower not in summary.lower():
                    return None
            
            # 키워드 분류
            classifications, matched_keywords = classify_article(title, summary)
            
            # ICH 관련 기사에 규제행정 분류 추가
            if not classifications:
                # ICH 뉴스는 기본적으로 규제/가이드라인 관련
                classifications = ["규제행정"]
                matched_keywords = ["ICH", "가이드라인"]
            
            return NewsArticle(
                title=title,
                link=link,
                published=published,
                source=self.source_name,
                summary=summary[:500] if summary else None,  # 요약 길이 제한
                classifications=classifications,
                matched_keywords=matched_keywords
            )
            
        except Exception as e:
            print(f"[DEBUG] RSS 엔트리 파싱 실패: {e}")
            return None
    
    def _parse_date(self, entry) -> datetime | None:
        """
        RSS 엔트리에서 날짜 파싱
        feedparser는 여러 날짜 형식을 자동으로 파싱
        """
        # published_parsed 사용 (feedparser가 자동 파싱)
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass
        
        # updated_parsed 사용
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except:
                pass
        
        # 문자열 직접 파싱 시도
        date_str = entry.get('published') or entry.get('updated') or entry.get('dc:date', '')
        if date_str:
            formats = [
                "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
                "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
                "%d %B %Y",                   # 11 December 2025
                "%Y-%m-%d",                   # 2025-12-11
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
        
        return None
    
    def get_all_news(self, days_back: int = 30) -> List[NewsArticle]:
        """
        키워드 필터 없이 모든 ICH 뉴스 수집
        규제 업데이트 모니터링용
        
        Args:
            days_back: 수집할 기간 (일수)
            
        Returns:
            NewsArticle 리스트
        """
        return self.fetch_news(query=None, days_back=days_back)
