# 약사공론 (KPA News) 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import time
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class KPANewsScraper(BaseScraper):
    """
    약사공론 (KPA News) 뉴스 스크래퍼
    
    지원 URL:
    - 기사 목록: https://www.kpanews.co.kr/article/list.asp
    - 검색: https://www.kpanews.co.kr/article/search4.asp?top_keyword=검색어
    """
    
    @property
    def source_name(self) -> str:
        return "KPA News"
    
    @property
    def base_url(self) -> str:
        return "https://www.kpanews.co.kr"
    
    @property
    def list_url(self) -> str:
        return f"{self.base_url}/article/list.asp"
    
    @property
    def search_url(self) -> str:
        return f"{self.base_url}/article/search4.asp"
    
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
    
    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        약사공론에서 뉴스 수집
        
        Args:
            query: 검색 키워드 (None이면 전체 기사 목록)
            days_back: 수집 기간 (None이면 자동 계산: 1일 / 월요일 3일)
            
        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # 검색 URL 또는 목록 URL 선택
        if query:
            encoded_query = query.replace(" ", "+")
            url = f"{self.search_url}?top_keyword={encoded_query}"
            print(f"[KPA] Searching for: '{query}' (days_back: {days_back})")
        else:
            url = self.list_url
            print(f"[KPA] Fetching article list (days_back: {days_back})")
        
        print(f"[KPA] Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
        
        # 재시도 로직 (최대 3회)
        soup = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    print(f"[KPA] HTTP error: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                break
                
            except requests.exceptions.Timeout:
                print(f"[KPA] Timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"[KPA] Max retries exceeded")
                    return []
            except Exception as e:
                print(f"[KPA] Request error: {e}")
                return []
        
        if soup is None:
            return []
        
        articles = []
        
        # 기사 목록 파싱 - 두 가지 방식 시도
        # 방식 1: 목록 페이지 (a[href*="show.asp"])
        article_links = soup.select('a[href*="show.asp?page="]')
        
        if article_links:
            print(f"[KPA] Found {len(article_links)} article links")
            for link in article_links:
                try:
                    article = self._parse_list_item(link, cutoff_date)
                    if article:
                        articles.append(article)
                except Exception as e:
                    continue
        else:
            # 방식 2: 검색 결과 페이지 (li[class^="article_list_"])
            article_items = soup.select('li[class^="article_list_"]')
            print(f"[KPA] Found {len(article_items)} search result items")
            
            for item in article_items:
                try:
                    article = self._parse_search_item(item, cutoff_date)
                    if article:
                        articles.append(article)
                except Exception as e:
                    continue
        
        # 중복 제거 (링크 기준)
        seen_links = set()
        unique_articles = []
        for article in articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[KPA] Collected {len(unique_articles)} articles")
        return unique_articles
    
    # KPANews 본문 CSS 선택자
    CONTENT_SELECTORS = ['#articleBody', '.article-body', '.article_body', '.news_body']
    
    def _parse_list_item(self, link_elem, cutoff_date: datetime) -> Optional[NewsArticle]:
        """기사 목록 아이템 파싱 (list.asp 페이지) + 본문 수집"""
        href = link_elem.get('href', '')
        if not href:
            return None
        
        # 전체 URL 생성
        if href.startswith('/'):
            full_link = f"{self.base_url}{href}"
        elif not href.startswith('http'):
            full_link = f"{self.base_url}/article/{href}"
        else:
            full_link = href
        
        # 제목 추출 (p.h1 또는 첫 번째 p 태그)
        title_elem = link_elem.select_one('p.h1')
        if not title_elem:
            p_tags = link_elem.select('p')
            title_elem = p_tags[0] if p_tags else None
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        # 날짜 추출 (p.botm span:first-child 또는 마지막 p의 첫 span)
        date_elem = link_elem.select_one('p.botm span')
        if not date_elem:
            p_tags = link_elem.select('p')
            if len(p_tags) >= 3:
                date_elem = p_tags[-1].select_one('span')
        
        date_text = date_elem.get_text(strip=True) if date_elem else ""
        published = self._parse_date(date_text)
        
        # 날짜 필터링
        if published and published < cutoff_date:
            return None
        
        # 요약 추출
        summary_elem = link_elem.select_one('p.h2')
        if not summary_elem:
            p_tags = link_elem.select('p')
            summary_elem = p_tags[1] if len(p_tags) > 1 else None
        
        summary = summary_elem.get_text(strip=True) if summary_elem else ""
        
        # 분류
        classifications, matched_keywords = classify_article(title, summary)
        if not classifications:
            classifications = ["업계뉴스"]
            matched_keywords = ["약사공론"]
        
        # 본문 수집
        content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)
        
        return NewsArticle(
            title=title,
            link=full_link,
            published=published,
            source=self.source_name,
            summary=summary[:300] if summary else "",
            full_text=content.get("full_text", ""),
            images=content.get("images", []),
            scrape_status=content.get("status", "pending"),
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def _parse_search_item(self, item, cutoff_date: datetime) -> Optional[NewsArticle]:
        """검색 결과 아이템 파싱 (search4.asp 페이지) + 본문 수집"""
        # 링크 추출
        link_tag = item.select_one('a[href^="show.asp"]')
        if not link_tag:
            return None
        
        href = link_tag.get('href', '')
        full_link = f"{self.base_url}/article/{href}"
        
        # 텍스트 영역에서 정보 추출
        divs = link_tag.select('div')
        text_div = divs[1] if len(divs) > 1 else None
        if not text_div:
            return None
        
        p_tags = text_div.select('p')
        if not p_tags:
            return None
        
        # 제목 (첫 번째 p 태그)
        title = p_tags[0].get_text(strip=True) if p_tags else ''
        if not title:
            return None
        
        # 날짜 (마지막 p 태그의 첫 번째 span)
        date_text = ''
        if p_tags:
            last_p = p_tags[-1]
            date_span = last_p.select_one('span')
            if date_span:
                date_text = date_span.get_text(strip=True)
        
        published = self._parse_date(date_text)
        
        # 날짜 필터링
        if published and published < cutoff_date:
            return None
        
        # 요약 (p 태그가 3개 이상이면 두 번째가 요약)
        summary = ''
        if len(p_tags) >= 3:
            summary = p_tags[1].get_text(strip=True)
        
        # 분류
        classifications, matched_keywords = classify_article(title, summary)
        if not classifications:
            classifications = ["업계뉴스"]
            matched_keywords = ["약사공론"]
        
        # 본문 수집
        content = self.fetch_article_content(full_link, self.CONTENT_SELECTORS)
        
        return NewsArticle(
            title=title,
            link=full_link,
            published=published,
            source=self.source_name,
            summary=summary[:300] if summary else "",
            full_text=content.get("full_text", ""),
            images=content.get("images", []),
            scrape_status=content.get("status", "pending"),
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        if not date_text:
            return None
        
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d",
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
    
    parser = argparse.ArgumentParser(description="KPA News Scraper")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 1 day or 3 on Monday)")
    args = parser.parse_args()
    
    scraper = KPANewsScraper()
    
    print("=" * 60)
    print("KPA News (약사공론) Scraper")
    print("=" * 60)
    
    articles = scraper.fetch_news(query=args.query, days_back=args.days)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:15], 1):
        date_str = article.published.strftime('%Y-%m-%d %H:%M') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:50]}...")
        print(f"   Link: {article.link}")
        print()
