# KPBMA Newsletter Scraper
# 한국제약바이오협회 뉴스레터 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import re
import sys
import os

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class KPBMAScraper(BaseScraper):
    """
    KPBMA (한국제약바이오협회) 뉴스레터 스크래퍼
    
    NOTE: KPBMA 뉴스레터 목록 페이지는 JavaScript로 렌더링됩니다.
    따라서 알려진 뉴스레터 URL 목록을 사용하거나,
    직접 URL을 제공받아 파싱합니다.
    """
    
    # 알려진 뉴스레터 URL 목록 (최신순)
    # 새 뉴스레터가 발행되면 이 목록을 업데이트
    KNOWN_NEWSLETTERS = [
        {
            "title": "12월 4주 뉴스레터, 범산업계 약가제도 개편...",
            "url": "https://stibee.com/api/v1.0/emails/share/2sAriUDbUicnvEpfQpkEk8F9XGprX58",
            "date": "2025/12/24"
        },
        {
            "title": "12월 2주 뉴스레터, 산업 발전을 위한 약가제도...",
            "url": "https://kpbma-info.stibee.com/p/13",
            "date": "2025/12/10"
        },
        {
            "title": "12월 1주 뉴스레터[특별호], 정부의 약가제도...",
            "url": "https://kpbma-info.stibee.com/p/11",
            "date": "2025/12/05"
        },
    ]
    
    @property
    def source_name(self) -> str:
        return "KPBMA Newsletter"
    
    @property
    def base_url(self) -> str:
        return "https://www.kpbma.or.kr"
    
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
        KPBMA 뉴스레터에서 뉴스 아이템 수집
        
        Args:
            query: 검색 키워드 (선택적)
            days_back: 수집할 기간 (일수), None이면 자동 계산
            
        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        all_articles = []
        
        print(f"[KPBMA] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        
        # 알려진 뉴스레터 목록에서 날짜 필터링
        newsletters = self._get_newsletters_in_range(cutoff_date)
        
        print(f"[KPBMA] Found {len(newsletters)} newsletters within date range")
        
        # 각 뉴스레터에서 뉴스 링크 추출
        for newsletter in newsletters:
            try:
                articles = self._parse_newsletter_content(
                    newsletter['url'], 
                    newsletter['title'],
                    newsletter['date'],
                    query
                )
                all_articles.extend(articles)
            except Exception as e:
                print(f"[KPBMA] Error parsing newsletter: {e}")
        
        # 중복 제거
        seen_links = set()
        unique_articles = []
        for article in all_articles:
            if article.link not in seen_links:
                seen_links.add(article.link)
                unique_articles.append(article)
        
        print(f"[KPBMA] Total collected: {len(unique_articles)} articles")
        return unique_articles
    
    def _get_newsletters_in_range(self, cutoff_date: datetime) -> List[dict]:
        """
        알려진 뉴스레터 목록에서 기간 내 뉴스레터 필터링
        """
        newsletters = []
        
        for nl in self.KNOWN_NEWSLETTERS:
            published_date = self._parse_date(nl['date'])
            
            if published_date and published_date >= cutoff_date:
                newsletters.append({
                    "title": nl['title'],
                    "url": nl['url'],
                    "date": published_date
                })
                print(f"[KPBMA] Newsletter in range: {nl['title'][:40]}... ({nl['date']})")
        
        return newsletters
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """날짜 파싱 (YYYY/MM/DD 형식)"""
        if not date_text:
            return None
        
        match = re.search(r'(\d{4})[/\-](\d{2})[/\-](\d{2})', date_text)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day)
            except ValueError:
                pass
        
        return None
    
    def _parse_newsletter_content(self, url: str, newsletter_title: str, 
                                   newsletter_date: datetime, query: str = None) -> List[NewsArticle]:
        """뉴스레터 콘텐츠에서 뉴스 링크 추출"""
        articles = []
        
        try:
            print(f"[KPBMA] Parsing newsletter content: {url[:50]}...")
            
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 뉴스레터 내의 모든 링크 추출
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # 빈 텍스트 또는 짧은 텍스트 건너뛰기
                if not text or len(text) < 10:
                    continue
                
                # Stibee/KPBMA 내부 링크 건너뛰기
                if 'stibee.com' in href or 'kpbma.or.kr' in href:
                    continue
                
                # 뉴스/기사 링크 필터링
                if self._is_news_link(href):
                    article = self._create_article(
                        text, href, newsletter_title, newsletter_date, query
                    )
                    if article:
                        articles.append(article)
            
            print(f"[KPBMA] Found {len(articles)} news links in newsletter")
            
        except Exception as e:
            print(f"[KPBMA] Error parsing newsletter: {e}")
        
        return articles
    
    def _is_news_link(self, href: str) -> bool:
        """뉴스 링크인지 확인"""
        news_domains = [
            'naver.com', 'daum.net', 'news', 'article',
            'mfds.go.kr', 'mohw.go.kr', 'hira.or.kr',
            'biz', 'newsis', 'yonhap', 'chosun', 'donga',
            'hankyung', 'mk.co.kr', 'edaily', 'mt.co.kr',
            'yna.co.kr', 'khan.co.kr', 'hani.co.kr',
            'dailypharm', 'yakup', 'health', 'medical'
        ]
        
        href_lower = href.lower()
        return any(domain in href_lower for domain in news_domains)
    
    # KPBMA 링크는 외부 뉴스 사이트로 연결되므로 Readability 사용
    CONTENT_SELECTORS = ['.article_body', '.news_body', '#articleBody', '.article-body']
    
    def _create_article(self, title: str, link: str, newsletter_title: str,
                        newsletter_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """NewsArticle 생성 + 본문 수집"""
        # 키워드 필터링
        if query and query.lower() not in title.lower():
            return None
        
        # 분류 수행
        classifications, matched_keywords = classify_article(title, "")
        
        if not classifications:
            classifications = ["업계뉴스"]
            matched_keywords = ["KPBMA", "제약"]
        
        # 본문 수집 (외부 링크에서)
        content = self.fetch_article_content(link, self.CONTENT_SELECTORS)
        
        return NewsArticle(
            title=title,
            link=link,
            published=newsletter_date,
            source=f"KPBMA-{newsletter_title[:25]}",
            summary=f"From KPBMA Newsletter: {newsletter_title}",
            full_text=content.get("full_text", ""),
            images=content.get("images", []),
            scrape_status=content.get("status", "pending"),
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def fetch_from_url(self, newsletter_url: str, title: str = "KPBMA Newsletter") -> List[NewsArticle]:
        """
        특정 뉴스레터 URL에서 직접 수집
        
        Args:
            newsletter_url: Stibee 뉴스레터 URL
            title: 뉴스레터 제목
            
        Returns:
            NewsArticle 리스트
        """
        print(f"[KPBMA] Fetching from URL: {newsletter_url[:50]}...")
        return self._parse_newsletter_content(newsletter_url, title, datetime.now())
    
    @classmethod
    def add_newsletter(cls, title: str, url: str, date: str):
        """
        새 뉴스레터를 목록에 추가 (런타임)
        
        Args:
            title: 뉴스레터 제목
            url: Stibee URL
            date: 발행일 (YYYY/MM/DD)
        """
        cls.KNOWN_NEWSLETTERS.insert(0, {
            "title": title,
            "url": url,
            "date": date
        })
        print(f"[KPBMA] Added newsletter: {title}")


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KPBMA Newsletter Scraper")
    parser.add_argument("--days", type=int, default=30,
                       help="Days back to scrape")
    parser.add_argument("--url", help="Specific newsletter URL to scrape")
    args = parser.parse_args()
    
    scraper = KPBMAScraper()
    
    print("=" * 60)
    print("KPBMA Newsletter Scraper")
    print("=" * 60)
    
    if args.url:
        articles = scraper.fetch_from_url(args.url)
    else:
        articles = scraper.fetch_news(days_back=args.days)
    
    print(f"\nTotal collected: {len(articles)} articles\n")
    
    for i, article in enumerate(articles[:15], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:50]}...")
        print(f"   Source: {article.source}")
        print(f"   Link: {article.link[:60]}...")
        print()
