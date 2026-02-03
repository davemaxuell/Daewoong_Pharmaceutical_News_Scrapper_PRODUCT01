# PMDA Updates Scraper with GPT Analysis
# PMDA (Pharmaceuticals and Medical Devices Agency - Japan) 업데이트 뉴스레터 스크래퍼

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


class PMDAScraper(BaseScraper):
    """
    PMDA Updates Scraper
    일본 PMDA (의약품의료기기종합기구) 뉴스레터 수집 및 분석
    
    수집 대상:
    - PMDA Updates (분기/월별 뉴스레터 PDF)
    - 최신 업데이트 및 Back Numbers
    """
    
    @property
    def source_name(self) -> str:
        return "PMDA Updates"
    
    @property
    def base_url(self) -> str:
        return "https://www.pmda.go.jp"
    
    @property
    def page_url(self) -> str:
        return "https://www.pmda.go.jp/english/int-activities/outline/0006.html"
    
    def fetch_news(self, query: str = None, days_back: int = 365, max_pdfs: int = 2) -> List[NewsArticle]:
        """
        PMDA Updates 뉴스레터 수집
        
        Args:
            query: 검색 키워드 (선택적)
            days_back: 수집할 기간 (일수) - 뉴스레터는 분기별이므로 넉넉하게 설정
            max_pdfs: 가져올 최대 PDF 수 (최신순, 기본값 2)
            
        Returns:
            NewsArticle 리스트 (PDF 링크 포함)
        """
        articles = []
        
        try:
            print(f"[PMDA] Fetching updates from: {self.page_url}")
            
            response = requests.get(
                self.page_url,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PDF 링크 찾기 (모든 /files/*.pdf 링크)
            pdf_links = soup.select('a[href*="/files/"][href$=".pdf"]')
            
            print(f"[PMDA] Found {len(pdf_links)} PDF links on page (will process max {max_pdfs})")
            
            for link in pdf_links:
                try:
                    article = self._parse_update_entry(link, query)
                    if article:
                        articles.append(article)
                except Exception as e:
                    print(f"[PMDA] Error parsing entry: {e}")
                    continue
            
            # 날짜순 정렬 (최신순)
            articles.sort(key=lambda x: x.published if x.published else datetime.min, reverse=True)
            
            # Limit to max_pdfs most recent
            if max_pdfs and len(articles) > max_pdfs:
                articles = articles[:max_pdfs]
                print(f"[PMDA] Limited to {max_pdfs} most recent updates")
            
            for article in articles:
                print(f"[PMDA] Added: {article.title}")
            
            print(f"[PMDA] Successfully collected {len(articles)} updates")
            
        except requests.RequestException as e:
            print(f"[PMDA] Request error: {e}")
        except Exception as e:
            print(f"[PMDA] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        return articles
    
    def _parse_update_entry(self, link_element, query: str = None) -> Optional[NewsArticle]:
        """
        PMDA Update 엔트리 파싱
        
        Args:
            link_element: BeautifulSoup link element
            query: 검색 키워드 (선택적)
            
        Returns:
            NewsArticle 또는 None
        """
        # 링크 텍스트에서 제목/날짜 추출
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
        
        # 날짜 파싱 (텍스트에서 추출: "March, 2025", "2025 Summer" 등)
        published = self._parse_date_from_title(title)
        
        # 키워드 필터링
        if query and query.lower() not in title.lower():
            return None
        
        # 분류 수행
        classifications, matched_keywords = classify_article(title, "PMDA Updates Newsletter")
        
        if not classifications:
            classifications = ["규제행정"]
            matched_keywords = ["PMDA", "Japan"]
        
        return NewsArticle(
            title=f"PMDA Updates - {title}",
            link=pdf_url,
            published=published,
            source=self.source_name,
            summary=f"PMDA Newsletter: {title} | PDF: {pdf_url}",
            classifications=classifications,
            matched_keywords=matched_keywords
        )
    
    def _parse_date_from_title(self, title: str) -> Optional[datetime]:
        """
        제목에서 날짜 추출
        
        지원 형식:
        - "March, 2025"
        - "2025 Summer", "2025 Autumn"
        - "February, 2025"
        
        Args:
            title: 파싱할 제목
            
        Returns:
            datetime 또는 None
        """
        # Month, Year 형식 (March, 2025)
        month_year_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)[,\s]+(\d{4})', title, re.IGNORECASE)
        if month_year_match:
            month_name = month_year_match.group(1)
            year = int(month_year_match.group(2))
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            month = month_map.get(month_name.lower())
            if month:
                return datetime(year, month, 1)
        
        # Year Season 형식 (2025 Summer)
        season_match = re.search(r'(\d{4})\s+(Spring|Summer|Autumn|Fall|Winter)', title, re.IGNORECASE)
        if season_match:
            year = int(season_match.group(1))
            season = season_match.group(2).lower()
            season_month = {
                'spring': 4, 'summer': 7, 'autumn': 10, 'fall': 10, 'winter': 1
            }
            month = season_month.get(season, 1)
            return datetime(year, month, 1)
        
        return None
    
    def fetch_latest_update(self) -> Optional[NewsArticle]:
        """
        가장 최근 PMDA Update 1개만 가져오기
        
        Returns:
            최신 NewsArticle 또는 None
        """
        articles = self.fetch_news(days_back=365)
        
        if not articles:
            print("[PMDA] No updates found")
            return None
        
        # 이미 날짜순 정렬되어 있음, 첫 번째가 최신
        latest = articles[0]
        print(f"[PMDA] Latest Update: {latest.title}")
        return latest
    
    def analyze_pdf_with_gpt(self, pdf_url: str, title: str = "") -> Dict[str, Any]:
        """
        PDF에서 텍스트를 추출하고 GPT로 요약 생성
        
        Args:
            pdf_url: PDF 파일 URL
            title: 문서 제목 (프롬프트에 포함)
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            # 1. PDF를 메모리로 다운로드
            print(f"[PMDA] Downloading PDF: {pdf_url}")
            response = requests.get(pdf_url, headers=self.get_headers(), timeout=120)
            response.raise_for_status()
            
            pdf_size_kb = len(response.content) / 1024
            print(f"[PMDA] PDF size: {pdf_size_kb:.1f} KB")
            
            # 2. PyMuPDF로 PDF 텍스트 추출
            print("[PMDA] Extracting text from PDF...")
            pdf_bytes = io.BytesIO(response.content)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            text_content = ""
            for page_num, page in enumerate(doc, 1):
                text_content += f"\n--- Page {page_num} ---\n"
                text_content += page.get_text()
            
            doc.close()
            
            # 텍스트가 너무 길면 잘라내기 (GPT 토큰 제한)
            max_chars = 50000  # PMDA PDF는 길 수 있음
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars] + "\n\n[... Text truncated due to length ...]"
            
            print(f"[PMDA] Extracted {len(text_content)} characters from PDF")
            
            # 3. OpenAI 클라이언트 초기화
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {"error": "OPENAI_API_KEY not found in environment variables"}
            
            client = OpenAI(api_key=api_key)
            
            # 4. GPT에 요약 요청
            print("[PMDA] Sending to GPT for summary...")
            
            prompt = f"""Summarize this PMDA (Pharmaceuticals and Medical Devices Agency, Japan) Updates newsletter: "{title}"

Below is the extracted text from the PDF document:

---
{text_content}
---

Please provide:
1. **Executive Summary**: A brief 2-3 sentence overview of the key highlights
2. **Key Topics**: List the main topics covered in this newsletter (bullet points)
3. **Regulatory Updates**: Any important regulatory changes or announcements
4. **International Activities**: Any international cooperation or harmonization efforts mentioned
5. **Important Dates/Deadlines**: Any upcoming deadlines or important dates mentioned

Please provide a clear, concise summary in English."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a pharmaceutical regulatory expert specializing in Japanese pharmaceutical regulations and PMDA (Pharmaceuticals and Medical Devices Agency) activities.

Your role is to summarize PMDA Updates newsletters, highlighting key regulatory changes, international activities, and important announcements from Japan's pharmaceutical regulatory authority.

Focus on:
- New drug approvals and regulatory decisions
- Safety information and pharmacovigilance updates
- International cooperation and harmonization activities
- Guidance documents and policy changes"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary_text = response.choices[0].message.content
            
            print("[PMDA] Summary complete!")
            
            return {
                "success": True,
                "title": title,
                "pdf_url": pdf_url,
                "summary": summary_text
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def fetch_latest_and_summarize(self) -> Dict[str, Any]:
        """
        최신 PMDA Update를 가져와서 GPT로 요약하는 통합 메서드
        
        Returns:
            요약 결과 딕셔너리
        """
        print("=" * 60)
        print("PMDA Updates - Latest Newsletter Summary")
        print("=" * 60)
        
        # 1. 최신 Update 가져오기
        latest = self.fetch_latest_update()
        
        if not latest:
            return {"error": "No PMDA Update found"}
        
        print(f"\n[PMDA] Summarizing: {latest.title}")
        print(f"[PMDA] URL: {latest.link}")
        print(f"[PMDA] Date: {latest.published}")
        print()
        
        # 2. GPT로 요약
        result = self.analyze_pdf_with_gpt(latest.link, latest.title)
        
        # 3. 결과에 메타데이터 추가
        result["published_date"] = latest.published.isoformat() if latest.published else None
        result["source"] = self.source_name
        
        return result


# 독립 실행 테스트
if __name__ == "__main__":
    scraper = PMDAScraper()
    
    print("=" * 60)
    print("PMDA Updates Scraper - GPT Summary Test")
    print("=" * 60)
    
    # 최신 Update 가져와서 GPT로 요약
    result = scraper.fetch_latest_and_summarize()
    
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
    else:
        print("\n" + "=" * 60)
        print("SUMMARY RESULT")
        print("=" * 60)
        print(f"\nTitle: {result.get('title', 'N/A')}")
        print(f"Date: {result.get('published_date', 'N/A')}")
        print(f"PDF: {result.get('pdf_url', 'N/A')}")
        print("\n" + "-" * 60)
        print("GPT Summary:")
        print("-" * 60)
        print(result.get('summary', 'No summary available'))
