# FDA Warning Letters Scraper
# FDA 경고장(Warning Letters) 스크래퍼 - CDER (의약품) 중심

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys
import time
import re

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
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
            centers: 수집할 센터 목록 (기본값: ["ALL"] - 모든 FDA 부서)
                    특정 부서만: ["CDER", "CBER"], 의약품/생물의약품만
        """
        if centers is None:
            centers = ["ALL"]  # 모든 FDA 부서 포함
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

        # FDA는 게시일(Posted Date) 기준으로 필터링 - 최근 게시된 경고장 캡처
        cutoff_date = datetime.now() - timedelta(days=days_back)

        print(f"[FDA WL] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        print(f"[FDA WL] Target centers: {', '.join(self.centers)}")

        # FDA RSS 피드가 더 이상 제공되지 않아 웹 스크래핑 사용
        print("[FDA WL] Using web scraping method")
        articles = self._fetch_from_web(days_back, query)

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

    def _fetch_letter_content(self, url: str, headers: dict) -> str:
        """
        개별 경고장 페이지에서 전체 내용 추출

        Args:
            url: 경고장 페이지 URL
            headers: HTTP 요청 헤더

        Returns:
            경고장 전체 내용 (텍스트)
        """
        max_retries = 2
        response = None

        for retry in range(max_retries + 1):
            try:
                # 재시도 시 더 긴 딜레이
                if retry > 0:
                    delay = 2 * retry  # 2, 4초
                    time.sleep(delay)

                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    break  # 성공, 진행
                elif retry < max_retries:
                    continue  # 재시도
                else:
                    return ""

            except Exception as e:
                if retry < max_retries:
                    continue
                return ""

        if not response or response.status_code != 200:
            return ""

        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            # FDA 경고장은 일반적으로 main 태그 내에 있음
            # 여러 방법으로 본문 추출 시도

            content_text = ""

            # Method 1: main 태그에서 추출
            main_elem = soup.find('main')
            if main_elem:
                # 불필요한 요소 제거
                for elem in main_elem.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'button', 'form']):
                    elem.decompose()

                # 네비게이션, 사이드바 등 제거
                for elem in main_elem.find_all(class_=['sidebar', 'navigation', 'breadcrumb', 'menu', 'nav']):
                    elem.decompose()

                content_text = main_elem.get_text(separator='\n', strip=True)

            # Method 2: article 태그에서 추출 (더 구체적)
            if not content_text or len(content_text) < 500:
                article_elem = soup.find('article')
                if article_elem:
                    for elem in article_elem.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                        elem.decompose()
                    content_text = article_elem.get_text(separator='\n', strip=True)

            # Method 3: Drupal specific - field--name-body
            if not content_text or len(content_text) < 500:
                body_field = soup.find('div', class_='field--name-body')
                if body_field:
                    content_text = body_field.get_text(separator='\n', strip=True)

            # Method 4: Look for content divs
            if not content_text or len(content_text) < 500:
                for class_name in ['content', 'main-content', 'page-content', 'article-content']:
                    content_div = soup.find('div', class_=class_name)
                    if content_div:
                        for elem in content_div.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                            elem.decompose()
                        text = content_div.get_text(separator='\n', strip=True)
                        if len(text) > len(content_text):
                            content_text = text

            if content_text:
                # 불필요한 공백 정리
                lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                text = '\n'.join(lines)

                # 중복된 공백 제거
                import re
                text = re.sub(r'\n{3,}', '\n\n', text)  # 3개 이상의 연속 줄바꿈을 2개로
                text = re.sub(r' {2,}', ' ', text)  # 2개 이상의 연속 공백을 1개로

                # 너무 긴 경우 제한 (AI 토큰 제한 고려)
                if len(text) > 15000:
                    text = text[:15000] + "\n\n[... content truncated for length ...]"

                # 최소 길이 체크 (너무 짧으면 실패로 간주)
                if len(text) > 200:
                    return text

            return ""

        except Exception as e:
            print(f"[FDA WL] Error extracting letter content: {e}")
            return ""

    def _fetch_from_web(self, days_back: int, query: str = None) -> List[NewsArticle]:
        """
        FDA Warning Letters 웹페이지에서 직접 스크래핑
        RSS 피드가 더 이상 제공되지 않아 HTML 테이블 직접 파싱으로 변경
        """
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # 단순화된 헤더 (테스트에서 작동 확인)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 여러 페이지 스크래핑 (최대 3페이지)
        for page_num in range(3):
            url = self.WARNING_LETTERS_URL
            if page_num > 0:
                url = f"{self.WARNING_LETTERS_URL}?page={page_num}"
            
            print(f"[FDA WL] Fetching page {page_num + 1}: {url}")
            
            # 재시도 로직
            response = None
            for retry in range(3):
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        break
                    print(f"[FDA WL] Got status {response.status_code}, retry {retry + 1}/3...")
                    time.sleep(2)
                except Exception as e:
                    print(f"[FDA WL] Request error: {e}, retry {retry + 1}/3...")
                    time.sleep(2)
            
            if not response or response.status_code != 200:
                print(f"[FDA WL] Failed to fetch page {page_num + 1} after 3 retries")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # FDA는 다양한 테이블 클래스 사용
            table = soup.find('table', class_='lcds-datatable')
            if not table:
                table = soup.find('table', class_='views-table')
            if not table:
                table = soup.find('table', class_='usa-table')
            if not table:
                table = soup.find('table')
            
            if not table:
                print(f"[FDA WL] No table found on page {page_num + 1}")
                break
            
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                rows = table.find_all('tr')[1:]  # 헤더 제외
            
            print(f"[FDA WL] Found {len(rows)} rows on page {page_num + 1}")
            
            found_old_article = False
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue
                    
                    # FDA Warning Letters 테이블 구조
                    posted_date_str = cells[0].get_text(strip=True)
                    issue_date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    company = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    issuing_office = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    subject = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                    
                    # 링크 추출
                    link_elem = cells[2].find('a') if len(cells) > 2 else None
                    if not link_elem:
                        for cell in cells:
                            link_elem = cell.find('a')
                            if link_elem:
                                break
                    
                    if not link_elem:
                        continue
                    
                    link = link_elem.get('href', '')
                    if link and not link.startswith('http'):
                        link = f"{self.BASE_URL}{link}"
                    
                    if not company and link_elem:
                        company = link_elem.get_text(strip=True)
                    
                    # 날짜 파싱 (Posted Date 우선 - 최근 게시된 경고장 캡처)
                    # Posted Date가 더 중요: FDA가 웹사이트에 게시한 날짜
                    published = self._parse_fda_date(posted_date_str) or self._parse_fda_date(issue_date_str)

                    if published and published < cutoff_date:
                        found_old_article = True
                        continue
                    
                    # Center 필터링
                    if self.centers and "all" not in [c.lower() for c in self.centers]:
                        center_matched = False
                        for center in self.centers:
                            if center.upper() in issuing_office.upper():
                                center_matched = True
                                break
                        if not center_matched:
                            continue
                    
                    # 키워드 필터링
                    if query:
                        search_text = f"{company} {subject} {issuing_office}".lower()
                        if query.lower() not in search_text:
                            continue
                    
                    # 제목 생성
                    title = f"[FDA Warning Letter] {company}"
                    if subject:
                        title = f"[FDA Warning Letter] {company} - {subject[:50]}"
                    
                    # 요약
                    summary = f"Company: {company}\nIssuing Office: {issuing_office}"
                    if subject:
                        summary += f"\nSubject: {subject}"
                    if issue_date_str:
                        summary += f"\nIssue Date: {issue_date_str}"
                    
                    # 분류
                    classifications, matched_keywords = classify_article(title, summary)
                    if not classifications:
                        classifications = ["FDA", "규제", "경고장"]
                        matched_keywords = ["FDA", "Warning Letter", issuing_office]
                    
                    # 전체 내용 가져오기 (AI 요약용)
                    full_text = self._fetch_letter_content(link, headers)
                    if not full_text:
                        # 폴백: 메타데이터만 사용
                        full_text = f"Company: {company}\n\nIssuing Office: {issuing_office}\n\nSubject: {subject}\n\nLetter Issue Date: {issue_date_str}"
                    
                    # 요청 간 딜레이 (rate limiting 방지)
                    time.sleep(0.5)
                    
                    articles.append(NewsArticle(
                        title=title,
                        link=link,
                        published=published,
                        source=self.source_name,
                        summary=summary,
                        full_text=full_text,
                        images=[],
                        scrape_status="success",
                        classifications=classifications,
                        matched_keywords=matched_keywords
                    ))
                    
                except Exception as e:
                    print(f"[FDA WL] Error parsing row: {e}")
                    continue
            
            # 오래된 기사만 발견되면 더 이상 페이지 스크래핑 중단
            if found_old_article and len(articles) > 0:
                print(f"[FDA WL] Reached articles older than {days_back} days, stopping pagination")
                break
                
            # 다음 페이지 요청 전 딜레이
            time.sleep(1)
        
        return articles
    
    def _parse_fda_date(self, date_str: str) -> Optional[datetime]:
        """FDA 날짜 문자열 파싱 (다양한 형식 지원)"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # 다양한 날짜 형식 시도
        date_formats = [
            "%m/%d/%Y",        # 01/15/2026
            "%m-%d-%Y",        # 01-15-2026
            "%B %d, %Y",       # January 15, 2026
            "%b %d, %Y",       # Jan 15, 2026
            "%Y-%m-%d",        # 2026-01-15
            "%d %B %Y",        # 15 January 2026
            "%d %b %Y",        # 15 Jan 2026
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None


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
