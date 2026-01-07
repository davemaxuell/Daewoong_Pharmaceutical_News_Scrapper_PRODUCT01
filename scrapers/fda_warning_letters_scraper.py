# FDA Warning Letters Scraper
# FDA 경고장(Warning Letters) 스크래퍼 - CDER (의약품) 중심

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys
import time

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    # 독립 실행 시
    from base_scraper import BaseScraper, NewsArticle


class FDAWarningLettersScraper(BaseScraper):
    """
    FDA Warning Letters 스크래퍼

    FDA의 경고장(Warning Letters)을 수집합니다.
    주로 CDER(Center for Drug Evaluation and Research)의 의약품 관련 경고장 수집

    경고장 유형:
    - CGMP violations (의약품 제조 및 품질관리 기준 위반)
    - Unapproved new drugs (미승인 신약)
    - Misbranding (표시 위반)
    - Adulteration (불순물)

    URL: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters
    """

    BASE_URL = "https://www.fda.gov"
    WARNING_LETTERS_URL = f"{BASE_URL}/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters"

    # FDA Centers (발급 기관)
    ISSUING_OFFICES = {
        "CDER": "Center for Drug Evaluation and Research",  # 의약품
        "CBER": "Center for Biologics Evaluation and Research",  # 생물의약품
        "CDRH": "Center for Devices and Radiological Health",  # 의료기기
        "CVM": "Center for Veterinary Medicine",  # 동물의약품
        "CFSAN": "Center for Food Safety and Applied Nutrition",  # 식품
        "CTP": "Center for Tobacco Products",  # 담배
        "ORA": "Office of Regulatory Affairs",  # 규제업무
    }

    def __init__(self, centers: List[str] = None):
        """
        FDA Warning Letters 스크래퍼 초기화

        Args:
            centers: 수집할 센터 목록 (기본값: ["CDER", "CBER"] - 의약품/생물의약품)
        """
        if centers is None:
            centers = ["CDER", "CBER"]  # 의약품 중심
        self.centers = [c.upper() for c in centers]

    @property
    def source_name(self) -> str:
        return "FDA Warning Letters"

    @property
    def base_url(self) -> str:
        return self.BASE_URL

    def _get_days_back(self) -> int:
        """요일에 따른 수집 기간 결정"""
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return 3
        return 1

    def fetch_news(self, query: str = None, days_back: int = None) -> List[NewsArticle]:
        """
        FDA Warning Letters 수집

        Args:
            query: 검색 키워드 (회사명, 주제 등)
            days_back: 수집 기간 (None이면 자동 계산)

        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()

        # FDA는 발급일(Letter Issue Date) 기준으로 필터링
        cutoff_date = datetime.now() - timedelta(days=days_back)

        print(f"[FDA WL] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        print(f"[FDA WL] Target centers: {', '.join(self.centers)}")

        # FDA 웹사이트는 자주 블록하므로 RSS를 우선 사용
        print("[FDA WL] Using RSS feed method (more reliable)")
        articles = self._fetch_from_rss(days_back, query)

        print(f"[FDA WL] Total collected: {len(articles)} warning letters")
        return articles

    def _parse_table_row(self, row, cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """테이블 행 파싱"""
        try:
            cells = row.find_all('td')
            if len(cells) < 5:
                return None

            # 컬럼: Posted Date, Letter Issue Date, Company Name, Issuing Office, Subject, Response Letter, Closeout Letter, Excerpt
            posted_date_str = cells[0].get_text(strip=True)
            issue_date_str = cells[1].get_text(strip=True)
            company = cells[2].get_text(strip=True)
            issuing_office = cells[3].get_text(strip=True)
            subject = cells[4].get_text(strip=True) if len(cells) > 4 else ""

            # 링크 추출
            link_elem = cells[2].find('a')
            if not link_elem:
                return None

            link = link_elem.get('href', '')
            if link and not link.startswith('http'):
                link = f"{self.BASE_URL}{link}"

            # 날짜 파싱 (Letter Issue Date 사용)
            published = None
            try:
                published = datetime.strptime(issue_date_str, "%m/%d/%Y")
            except:
                try:
                    published = datetime.strptime(posted_date_str, "%m/%d/%Y")
                except:
                    pass

            # 날짜 필터링
            if published and published < cutoff_date:
                return None

            # Center 필터링 (CDER, CBER 등)
            if self.centers and "all" not in [c.lower() for c in self.centers]:
                # issuing_office에서 약어 추출
                office_matched = False
                for center_abbr in self.centers:
                    if center_abbr in issuing_office.upper():
                        office_matched = True
                        break

                if not office_matched:
                    return None

            # 키워드 필터링
            if query:
                search_text = f"{company} {subject}".lower()
                if query.lower() not in search_text:
                    return None

            # 제목 생성
            title = f"[FDA Warning Letter] {company} - {subject[:60]}"

            # 요약
            summary = f"Company: {company}\nIssuing Office: {issuing_office}\nSubject: {subject}\nIssue Date: {issue_date_str}"

            # 분류
            classifications, matched_keywords = classify_article(title, summary)
            if not classifications:
                # 기본 분류
                classifications = ["FDA", "규제", "경고장"]
                matched_keywords = ["FDA", "Warning Letter", issuing_office]

            return NewsArticle(
                title=title,
                link=link,
                published=published,
                source=self.source_name,
                summary=summary,
                full_text=f"Company: {company}\n\nIssuing Office: {issuing_office}\n\nSubject: {subject}\n\nLetter Issue Date: {issue_date_str}\nPosted Date: {posted_date_str}",
                images=[],
                scrape_status="success",
                classifications=classifications,
                matched_keywords=matched_keywords
            )

        except Exception as e:
            print(f"[FDA WL] Error parsing row: {e}")
            return None

    def _fetch_from_rss(self, days_back: int, query: str = None) -> List[NewsArticle]:
        """
        RSS 피드에서 경고장 수집
        FDA는 여러 RSS 피드 제공, Warning Letters 전용 피드 사용
        """
        # FDA Warning Letters RSS 피드들 (여러 개 시도)
        RSS_URLS = [
            "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/warning-letters/rss.xml",
            "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters.rss",
        ]

        articles = []

        for RSS_URL in RSS_URLS:
            try:
                print(f"[FDA WL] Trying RSS feed: {RSS_URL}")

                # 브라우저처럼 보이도록 헤더 개선
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }

                response = requests.get(RSS_URL, headers=headers, timeout=30, allow_redirects=True)

                if response.status_code == 404:
                    print(f"[FDA WL] RSS feed not found at {RSS_URL}, trying next...")
                    continue

                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'xml')
                items = soup.find_all('item')

                print(f"[FDA WL] Found {len(items)} items in RSS feed")

                if len(items) > 0:
                    # RSS 피드에서 데이터를 찾았으면 파싱 시작
                    cutoff_date = datetime.now() - timedelta(days=days_back)

                    for item in items:
                        try:
                            title_elem = item.find('title')
                            link_elem = item.find('link')
                            pubdate_elem = item.find('pubDate')
                            description_elem = item.find('description')

                            if not title_elem or not link_elem:
                                continue

                            title = title_elem.get_text(strip=True)
                            link = link_elem.get_text(strip=True)
                            description = description_elem.get_text(strip=True) if description_elem else ""

                            # 날짜 파싱 (RSS pubDate format: "Mon, 06 Jan 2026 00:00:00 +0000")
                            published = None
                            if pubdate_elem:
                                try:
                                    pubdate_str = pubdate_elem.get_text(strip=True)
                                    # RFC 2822 format
                                    published = datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=None)
                                except:
                                    pass

                            # 날짜 필터링
                            if published and published < cutoff_date:
                                continue

                            # Center 필터링
                            if self.centers and "all" not in [c.lower() for c in self.centers]:
                                center_matched = False
                                for center in self.centers:
                                    if center.upper() in title.upper() or center.upper() in description.upper():
                                        center_matched = True
                                        break

                                if not center_matched:
                                    continue

                            # 분류
                            classifications, matched_keywords = classify_article(title, description)
                            if not classifications:
                                classifications = ["FDA", "규제", "경고장"]
                                matched_keywords = ["FDA", "Warning Letter"]

                            articles.append(NewsArticle(
                                title=f"[FDA WL] {title}",
                                link=link,
                                published=published,
                                source=self.source_name,
                                summary=description,
                                full_text=description,
                                images=[],
                                scrape_status="success",
                                classifications=classifications,
                                matched_keywords=matched_keywords
                            ))

                        except Exception as e:
                            print(f"[FDA WL] Error parsing RSS item: {e}")
                            continue

                    # 성공적으로 아이템을 찾았으면 루프 종료
                    break

            except Exception as e:
                print(f"[FDA WL] Error with RSS URL {RSS_URL}: {e}")
                continue

        return articles


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FDA Warning Letters Scraper")
    parser.add_argument("--centers", nargs="+", default=["CDER", "CBER"],
                       help="Centers to monitor (default: CDER CBER)")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 1 day or 3 on Monday)")
    args = parser.parse_args()

    scraper = FDAWarningLettersScraper(centers=args.centers)

    print("=" * 60)
    print("FDA Warning Letters Scraper")
    print("=" * 60)

    articles = scraper.fetch_news(days_back=args.days)

    print(f"\nTotal collected: {len(articles)} warning letters\n")

    for i, article in enumerate(articles[:10], 1):
        date_str = article.published.strftime('%Y-%m-%d') if article.published else 'N/A'
        print(f"{i}. [{date_str}] {article.title[:80]}...")
        print(f"   {article.link}")
        print()
