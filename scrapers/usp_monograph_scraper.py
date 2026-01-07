# USP Pending Monograph Scraper
# USP-NF Pending Monograph Program (미국약전 펜딩 모노그래프 프로그램) PDF 수집

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import time
import re
import sys
import os
import io
import fitz  # PyMuPDF for PDF text extraction
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 상위 디렉토리의 keywords 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keywords import classify_article

from .base_scraper import BaseScraper, NewsArticle


class USPMonographScraper(BaseScraper):
    """
    USP-NF Pending Monograph Scraper
    미국약전 펜딩 모노그래프 수집
    
    수집 대상:
    - Pending Revision Notices (PDF 문서)
    - 각 모노그래프의 게시일(posted date) 및 PDF 링크
    """
    
    @property
    def source_name(self) -> str:
        return "USP Pending Monographs"
    
    @property
    def base_url(self) -> str:
        return "https://www.uspnf.com"
    
    @property
    def page_url(self) -> str:
        return "https://www.uspnf.com/pending-monographs/pending-monograph-program"
    
    @property
    def revision_bulletins_url(self) -> str:
        return "https://www.uspnf.com/official-text/revision-bulletins"
    
    def fetch_news(self, query: str = None, days_back: int = 7) -> List[NewsArticle]:
        """
        USP 펜딩 모노그래프 수집
        
        Args:
            query: 검색 키워드 (선택적, 제목 필터링용)
            days_back: 수집할 기간 (일수)
            
        Returns:
            NewsArticle 리스트 (PDF 링크 포함)
        """
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            print(f"[USP] Fetching pending monographs from: {self.page_url}")
            
            response = requests.get(
                self.page_url,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PDF 링크가 있는 모든 li 요소 찾기
            pdf_links = soup.select('a[href$=".pdf"]')
            
            print(f"[USP] Found {len(pdf_links)} PDF links")
            
            for link in pdf_links:
                try:
                    article = self._parse_pdf_entry(link, cutoff_date, query)
                    if article:
                        articles.append(article)
                        print(f"[USP] Added: {article.title[:50]}...")
                except Exception as e:
                    print(f"[USP] Error parsing entry: {e}")
                    continue
            
            print(f"[USP] Successfully collected {len(articles)} monographs")
            
        except requests.RequestException as e:
            print(f"[USP] Request error: {e}")
        except Exception as e:
            print(f"[USP] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        return articles
    
    def _parse_pdf_entry(self, link_element, cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """
        PDF 링크 엔트리 파싱
        
        Args:
            link_element: BeautifulSoup link element
            cutoff_date: 필터링할 기준 날짜
            query: 검색 키워드 (선택적)
            
        Returns:
            NewsArticle 또는 None
        """
        # 제목 추출 (링크 텍스트)
        title = link_element.get_text(strip=True)
        if not title:
            return None
        
        # PDF URL 추출
        pdf_url = link_element.get('href', '')
        if not pdf_url:
            return None
        
        # 상대 경로인 경우 절대 경로로 변환
        if pdf_url.startswith('/'):
            pdf_url = self.base_url + pdf_url
        
        # 부모 li 요소에서 게시일 추출
        parent_li = link_element.find_parent('li')
        posted_date = None
        
        if parent_li:
            li_text = parent_li.get_text()
            posted_date = self._parse_posted_date(li_text)
        
        # 날짜 필터링
        if posted_date and posted_date < cutoff_date:
            return None
        
        # 키워드 필터링 (query가 있는 경우)
        if query and query.lower() not in title.lower():
            return None
        
        # 분류 수행
        classifications, matched_keywords = classify_article(title, "")
        
        # 요약 생성 (PDF URL 포함)
        summary = f"PDF: {pdf_url}"
        if posted_date:
            summary = f"Posted: {posted_date.strftime('%Y-%m-%d')} | {summary}"
        
        return NewsArticle(
            title=title,
            link=pdf_url,
            published=posted_date,
            source=self.source_name,
            summary=summary,
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def _parse_posted_date(self, text: str) -> Optional[datetime]:
        """
        '(posted DD-Mon-YYYY)' 형식의 날짜 파싱
        
        Args:
            text: 파싱할 텍스트
            
        Returns:
            datetime 또는 None
        """
        # 정규식으로 날짜 추출: (posted 25-Apr-2025)
        match = re.search(r'\(posted\s+(\d{1,2})-(\w{3})-(\d{4})\)', text, re.IGNORECASE)
        
        if match:
            day = int(match.group(1))
            month_str = match.group(2)
            year = int(match.group(3))
            
            # 월 이름을 숫자로 변환
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            
            month = month_map.get(month_str.lower())
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    pass
        
        return None
    
    def fetch_revision_bulletins(self, query: str = None, days_back: int = 30) -> List[NewsArticle]:
        """
        USP Revision Bulletins 수집 (공식 개정 고시)
        
        Revision Bulletins는 USP-NF의 가속화된 공식 개정 사항입니다.
        Pending Monographs와 달리 이미 공식 발효된 변경 사항입니다.
        
        Args:
            query: 검색 키워드 (선택적, 제목 필터링용)
            days_back: 수집할 기간 (일수)
            
        Returns:
            NewsArticle 리스트 (PDF 링크 포함)
        """
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            print(f"[USP-RB] Fetching revision bulletins from: {self.revision_bulletins_url}")
            
            response = requests.get(
                self.revision_bulletins_url,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PDF 링크가 있는 모든 li 요소에서 Notice PDF 찾기
            pdf_links = soup.select('a[href$=".pdf"]')
            
            print(f"[USP-RB] Found {len(pdf_links)} PDF links")
            
            for link in pdf_links:
                try:
                    article = self._parse_revision_bulletin_entry(link, cutoff_date, query)
                    if article:
                        articles.append(article)
                        print(f"[USP-RB] Added: {article.title[:50]}...")
                except Exception as e:
                    print(f"[USP-RB] Error parsing entry: {e}")
                    continue
            
            print(f"[USP-RB] Successfully collected {len(articles)} revision bulletins")
            
        except requests.RequestException as e:
            print(f"[USP-RB] Request error: {e}")
        except Exception as e:
            print(f"[USP-RB] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        return articles
    
    def _parse_revision_bulletin_entry(self, link_element, cutoff_date: datetime, query: str = None) -> Optional[NewsArticle]:
        """
        Revision Bulletin 엔트리 파싱
        
        형식: (posted DD-Mon-YYYY; official DD-Mon-YYYY)
        
        Args:
            link_element: BeautifulSoup link element
            cutoff_date: 필터링할 기준 날짜
            query: 검색 키워드 (선택적)
            
        Returns:
            NewsArticle 또는 None
        """
        # 제목 추출 (링크 텍스트)
        title = link_element.get_text(strip=True)
        
        # "Notice" 링크인지 확인 (Notice PDF만 수집)
        if title.lower() == "notice" or not title:
            # 부모 li에서 실제 제목 찾기
            parent_li = link_element.find_parent('li')
            if parent_li:
                # li의 첫 번째 텍스트나 다른 링크에서 제목 추출
                li_text = parent_li.get_text(strip=True)
                # "Notice"와 날짜 부분 제거
                title = re.sub(r'\s*Notice.*$', '', li_text)
                title = re.sub(r'\s*\(posted.*$', '', title)
                title = title.strip()
        
        if not title:
            return None
        
        # PDF URL 추출
        pdf_url = link_element.get('href', '')
        if not pdf_url:
            return None
        
        # 상대 경로인 경우 절대 경로로 변환
        if pdf_url.startswith('/'):
            pdf_url = self.base_url + pdf_url
        
        # 부모 li 요소에서 날짜 추출
        parent_li = link_element.find_parent('li')
        posted_date = None
        official_date = None
        
        if parent_li:
            li_text = parent_li.get_text()
            posted_date, official_date = self._parse_bulletin_dates(li_text)
        
        # 날짜 필터링 (official date 기준, 없으면 posted date)
        filter_date = official_date or posted_date
        if filter_date and filter_date < cutoff_date:
            return None
        
        # 키워드 필터링 (query가 있는 경우)
        if query and query.lower() not in title.lower():
            return None
        
        # 분류 수행
        classifications, matched_keywords = classify_article(title, "")
        
        # 요약 생성 (PDF URL + 날짜 정보)
        summary_parts = []
        if posted_date:
            summary_parts.append(f"Posted: {posted_date.strftime('%Y-%m-%d')}")
        if official_date:
            summary_parts.append(f"Official: {official_date.strftime('%Y-%m-%d')}")
        summary_parts.append(f"PDF: {pdf_url}")
        summary = " | ".join(summary_parts)
        
        return NewsArticle(
            title=title,
            link=pdf_url,
            published=official_date or posted_date,  # official date 우선
            source="USP Revision Bulletins",
            summary=summary,
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def _parse_bulletin_dates(self, text: str) -> tuple:
        """
        '(posted DD-Mon-YYYY; official DD-Mon-YYYY)' 형식의 날짜 파싱
        
        Args:
            text: 파싱할 텍스트
            
        Returns:
            (posted_date, official_date) 튜플
        """
        posted_date = None
        official_date = None
        
        # posted 날짜 추출
        posted_match = re.search(r'posted\s+(\d{1,2})-(\w{3})-(\d{4})', text, re.IGNORECASE)
        if posted_match:
            posted_date = self._convert_date_parts(
                posted_match.group(1), 
                posted_match.group(2), 
                posted_match.group(3)
            )
        
        # official 날짜 추출
        official_match = re.search(r'official\s+(\d{1,2})-(\w{3})-(\d{4})', text, re.IGNORECASE)
        if official_match:
            official_date = self._convert_date_parts(
                official_match.group(1), 
                official_match.group(2), 
                official_match.group(3)
            )
        
        return posted_date, official_date
    
    def _convert_date_parts(self, day_str: str, month_str: str, year_str: str) -> Optional[datetime]:
        """날짜 파트를 datetime으로 변환"""
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        try:
            day = int(day_str)
            month = month_map.get(month_str.lower())
            year = int(year_str)
            
            if month:
                return datetime(year, month, day)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def fetch_all_pdfs(self, download_dir: str = None, days_back: int = 7) -> List[dict]:
        """
        PDF 파일 다운로드 (선택적 기능)
        
        Args:
            download_dir: 다운로드 디렉토리 (None이면 다운로드 안함)
            days_back: 수집할 기간 (일수)
            
        Returns:
            다운로드된 PDF 정보 리스트
        """
        articles = self.fetch_news(days_back=days_back)
        downloaded = []
        
        if download_dir:
            os.makedirs(download_dir, exist_ok=True)
            
            for article in articles:
                try:
                    pdf_url = article.link
                    filename = pdf_url.split('/')[-1]
                    filepath = os.path.join(download_dir, filename)
                    
                    print(f"[USP] Downloading: {filename}")
                    
                    response = requests.get(pdf_url, headers=self.get_headers(), timeout=60)
                    response.raise_for_status()
                    
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded.append({
                        'title': article.title,
                        'filename': filename,
                        'filepath': filepath,
                        'url': pdf_url,
                        'posted_date': article.published.isoformat() if article.published else None
                    })
                    
                    print(f"[USP] Downloaded: {filepath}")
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    print(f"[USP] Failed to download {article.link}: {e}")
        
        return downloaded
    
    def fetch_latest_pdf(self) -> Optional[NewsArticle]:
        """
        가장 최근에 게시된 PDF 1개만 가져오기
        
        Returns:
            최신 NewsArticle 또는 None
        """
        # 최근 365일간 모노그래프 수집
        articles = self.fetch_news(days_back=365)
        
        if not articles:
            print("[USP] No articles found")
            return None
        
        # 날짜가 있는 것들 중 가장 최신 것 선택
        dated_articles = [a for a in articles if a.published is not None]
        
        if dated_articles:
            # 날짜순 정렬 (최신순)
            dated_articles.sort(key=lambda x: x.published, reverse=True)
            latest = dated_articles[0]
            print(f"[USP] Latest PDF: {latest.title} (posted {latest.published.strftime('%Y-%m-%d')})")
            return latest
        else:
            # 날짜 없는 경우 첫 번째 것 반환 (페이지 순서상 최신)
            print(f"[USP] Latest PDF (no date): {articles[0].title}")
            return articles[0]
    
    def analyze_pdf_with_gpt(self, pdf_url: str, title: str = "") -> Dict[str, Any]:
        """
        PDF에서 텍스트를 추출하고 GPT로 제약 규정 변경 사항 분석
        (Text Extraction + Chat Completions API 방식)
        
        Args:
            pdf_url: PDF 파일 URL
            title: 문서 제목 (프롬프트에 포함)
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            # 1. PDF를 메모리로 다운로드
            print(f"[USP] Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, headers=self.get_headers(), timeout=60)
            response.raise_for_status()
            
            pdf_size_kb = len(response.content) / 1024
            print(f"[USP] PDF size: {pdf_size_kb:.1f} KB")
            
            # 2. PyMuPDF로 PDF 텍스트 추출 (메모리에서 직접)
            print("[USP] Extracting text from PDF...")
            pdf_bytes = io.BytesIO(response.content)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            text_content = ""
            for page_num, page in enumerate(doc, 1):
                text_content += f"\n--- Page {page_num} ---\n"
                text_content += page.get_text()
            
            doc.close()
            
            # 텍스트가 너무 길면 잘라내기 (GPT 토큰 제한)
            max_chars = 30000  # 약 7500 토큰
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars] + "\n\n[... Text truncated due to length ...]"
            
            print(f"[USP] Extracted {len(text_content)} characters from PDF")
            
            # 3. OpenAI 클라이언트 초기화
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {"error": "OPENAI_API_KEY not found in environment variables"}
            
            client = OpenAI(api_key=api_key)
            
            # 4. GPT에 분석 요청
            print("[USP] Sending to GPT for analysis...")
            
            prompt = f"""Analyze this USP pending monograph revision notice: "{title}"

Below is the extracted text from the PDF document:

---
{text_content}
---

Please tell me:
1. **Summary**: What is this monograph about?
2. **Key Changes**: What specific changes are being proposed to pharmaceutical rules/standards?
3. **Impact**: How will this affect pharmaceutical manufacturers or drug quality?
4. **Timeline**: When will these changes take effect (if mentioned)?

Please provide a clear, concise analysis in English."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a pharmaceutical regulatory expert specializing in USP-NF (United States Pharmacopeia - National Formulary) monographs.

Your role is to analyze pending monograph revision notices and clearly explain what changes are being proposed to pharmaceutical standards and regulations.

Focus on:
- What specific tests, methods, or specifications are being changed
- Why these changes are important for drug quality and safety
- Any new requirements being added or old ones being removed
- Impact on pharmaceutical manufacturers"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content
            
            print("[USP] Analysis complete!")
            
            return {
                "success": True,
                "title": title,
                "pdf_url": pdf_url,
                "analysis": analysis_text
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def fetch_latest_and_analyze(self) -> Dict[str, Any]:
        """
        최신 PDF를 가져와서 GPT로 분석하는 통합 메서드
        
        Returns:
            분석 결과 딕셔너리
        """
        print("=" * 60)
        print("USP Pending Monograph - Latest PDF Analysis")
        print("=" * 60)
        
        # 1. 최신 PDF 가져오기
        latest = self.fetch_latest_pdf()
        
        if not latest:
            return {"error": "No PDF found"}
        
        print(f"\n[USP] Analyzing: {latest.title}")
        print(f"[USP] URL: {latest.link}")
        print(f"[USP] Posted: {latest.published}")
        print()
        
        # 2. GPT로 분석
        result = self.analyze_pdf_with_gpt(latest.link, latest.title)
        
        # 3. 결과에 메타데이터 추가
        result["posted_date"] = latest.published.isoformat() if latest.published else None
        
        return result
    
    def fetch_latest_bulletin(self) -> Optional[NewsArticle]:
        """
        가장 최근에 게시된 Revision Bulletin 1개만 가져오기
        
        Returns:
            최신 NewsArticle 또는 None
        """
        # 최근 365일간 Revision Bulletins 수집
        articles = self.fetch_revision_bulletins(days_back=365)
        
        if not articles:
            print("[USP-RB] No bulletins found")
            return None
        
        # 날짜가 있는 것들 중 가장 최신 것 선택 (official date 기준)
        dated_articles = [a for a in articles if a.published is not None]
        
        if dated_articles:
            # 날짜순 정렬 (최신순)
            dated_articles.sort(key=lambda x: x.published, reverse=True)
            latest = dated_articles[0]
            print(f"[USP-RB] Latest Bulletin: {latest.title} (official {latest.published.strftime('%Y-%m-%d')})")
            return latest
        else:
            # 날짜 없는 경우 첫 번째 것 반환
            print(f"[USP-RB] Latest Bulletin (no date): {articles[0].title}")
            return articles[0]
    
    def fetch_latest_bulletin_and_analyze(self) -> Dict[str, Any]:
        """
        최신 Revision Bulletin을 가져와서 GPT로 분석하는 통합 메서드
        
        Returns:
            분석 결과 딕셔너리
        """
        print("=" * 60)
        print("USP Revision Bulletin - Latest PDF Analysis")
        print("=" * 60)
        
        # 1. 최신 Bulletin 가져오기
        latest = self.fetch_latest_bulletin()
        
        if not latest:
            return {"error": "No Revision Bulletin found"}
        
        print(f"\n[USP-RB] Analyzing: {latest.title}")
        print(f"[USP-RB] URL: {latest.link}")
        print(f"[USP-RB] Official Date: {latest.published}")
        print()
        
        # 2. GPT로 분석
        result = self.analyze_pdf_with_gpt(latest.link, latest.title)
        
        # 3. 결과에 메타데이터 추가
        result["official_date"] = latest.published.isoformat() if latest.published else None
        result["source"] = "USP Revision Bulletins"
        
        return result


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="USP Scraper - GPT Analysis")
    parser.add_argument("--type", choices=["pending", "bulletin"], default="bulletin",
                       help="Type of analysis: 'pending' for Pending Monographs, 'bulletin' for Revision Bulletins")
    args = parser.parse_args()
    
    scraper = USPMonographScraper()
    
    if args.type == "pending":
        print("=" * 60)
        print("USP Pending Monograph - GPT Analysis")
        print("=" * 60)
        result = scraper.fetch_latest_and_analyze()
    else:
        print("=" * 60)
        print("USP Revision Bulletin - GPT Analysis")
        print("=" * 60)
        result = scraper.fetch_latest_bulletin_and_analyze()
    
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
    else:
        print("\n" + "=" * 60)
        print("ANALYSIS RESULT")
        print("=" * 60)
        print(f"\nTitle: {result.get('title', 'N/A')}")
        print(f"Date: {result.get('official_date') or result.get('posted_date', 'N/A')}")
        print(f"PDF: {result.get('pdf_url', 'N/A')}")
        print("\n" + "-" * 60)
        print("GPT Analysis:")
        print("-" * 60)
        print(result.get('analysis', 'No analysis available'))
