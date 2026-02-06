# KPBMA Newsletter Scraper
# 한국제약바이오협회 뉴스레터 스크래퍼

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import re
import sys
import os
import json

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class KPBMAScraper(BaseScraper):
    """
    KPBMA (한국제약바이오협회) 뉴스레터 스크래퍼

    API 엔드포인트를 사용하여 뉴스레터 목록을 동적으로 가져옵니다.
    API: https://www.kpbma.or.kr/api/multimedia/newsLetter/lists
    """

    # API 엔드포인트
    NEWSLETTER_API = "https://www.kpbma.or.kr/api/multimedia/newsLetter/lists"
    
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
        API에서 뉴스레터 목록을 가져와 기간 내 뉴스레터 필터링
        """
        newsletters = []

        try:
            print(f"[KPBMA] Fetching newsletters from API...")
            response = requests.get(
                self.NEWSLETTER_API,
                headers=self.get_headers(),
                params={"start": 0},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("data", []):
                title = item.get("b_subject", "")
                # b_ext0 또는 b_ext5에 Stibee URL이 있음
                url = item.get("b_ext0") or item.get("b_ext5") or ""
                date_str = item.get("b_regdate", "")

                if not title or not url:
                    continue

                published_date = self._parse_date(date_str)

                if published_date and published_date >= cutoff_date:
                    newsletters.append({
                        "title": title,
                        "url": url,
                        "date": published_date
                    })
                    print(f"[KPBMA] Newsletter in range: {title[:40]}... ({date_str})")

            print(f"[KPBMA] API returned {len(data.get('data', []))} newsletters total")

        except Exception as e:
            print(f"[KPBMA] Error fetching from API: {e}")
            # API 실패 시 빈 목록 반환
            return []

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
    
    def fetch_all_newsletters(self) -> List[dict]:
        """
        API에서 모든 뉴스레터 목록을 가져옴 (날짜 필터 없음)

        Returns:
            뉴스레터 정보 리스트 [{"title": ..., "url": ..., "date": ...}, ...]
        """
        newsletters = []

        try:
            print(f"[KPBMA] Fetching all newsletters from API...")
            response = requests.get(
                self.NEWSLETTER_API,
                headers=self.get_headers(),
                params={"start": 0},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("data", []):
                title = item.get("b_subject", "")
                url = item.get("b_ext0") or item.get("b_ext5") or ""
                date_str = item.get("b_regdate", "")

                if title and url:
                    newsletters.append({
                        "title": title,
                        "url": url,
                        "date": date_str
                    })

            print(f"[KPBMA] Found {len(newsletters)} newsletters")

        except Exception as e:
            print(f"[KPBMA] Error fetching from API: {e}")

        return newsletters


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
