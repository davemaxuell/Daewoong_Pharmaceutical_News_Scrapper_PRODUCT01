# 기본 스크래퍼 인터페이스 및 공통 데이터 클래스

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


@dataclass
class NewsArticle:
    """수집할 기사 데이터 클래스 (full_text 포함)"""
    title: str
    link: str
    published: Optional[datetime]
    source: str
    summary: Optional[str] = None
    full_text: Optional[str] = None
    images: list = field(default_factory=list)
    scrape_status: str = "pending"  # pending, success, failed
    classifications: list = field(default_factory=list)
    matched_keywords: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """JSON 직렬화를 위한 딕셔너리 변환"""
        return {
            "title": self.title,
            "link": self.link,
            "published": self.published.isoformat() if self.published else None,
            "source": self.source,
            "summary": self.summary,
            "full_text": self.full_text,
            "images": self.images,
            "scrape_status": self.scrape_status,
            "classifications": self.classifications,
            "matched_keywords": self.matched_keywords
        }


class BaseScraper(ABC):
    """
    모든 뉴스 스크래퍼의 기본 인터페이스
    각 뉴스 소스별 스크래퍼는 이 클래스를 상속받아 구현
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """뉴스 소스 이름 (예: 'KPA News', 'Daily Pharm')"""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """뉴스 사이트 기본 URL"""
        pass
    
    @abstractmethod
    def fetch_news(self, query: str, days_back: int = 1) -> List[NewsArticle]:
        """
        뉴스 수집 메서드
        
        Args:
            query: 검색 키워드
            days_back: 수집할 기간 (일수)
            
        Returns:
            NewsArticle 리스트
        """
        pass
    
    def get_headers(self) -> dict:
        """공통 HTTP 헤더"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch_article_content(self, url: str, selectors: list = None) -> dict:
        """
        공통 기사 본문 추출 메서드
        
        Args:
            url: 기사 URL
            selectors: CSS 선택자 목록 (우선순위 순)
            
        Returns:
            {"full_text": str, "images": list, "status": str}
        """
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=15)
            
            # 인코딩 결정 (우선순위: Content-Type 헤더 > UTF-8 > apparent_encoding)
            content_type = response.headers.get('Content-Type', '')
            if 'charset=' in content_type:
                response.encoding = content_type.split('charset=')[-1].split(';')[0].strip()
            elif 'euc-kr' in content_type.lower() or 'euckr' in content_type.lower():
                response.encoding = 'euc-kr'
            else:
                response.encoding = 'utf-8'  # 대부분의 한국 사이트는 UTF-8
            
            if response.status_code != 200:
                return {"full_text": "", "images": [], "status": "failed"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 선택자로 본문 찾기
            full_text = ""
            if selectors:
                for selector in selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        full_text = content_elem.get_text(separator='\n', strip=True)
                        break
            
            # 선택자 실패 시 Readability 사용
            if not full_text:
                try:
                    from readability import Document
                    doc = Document(response.text)
                    main_html = doc.summary()
                    main_soup = BeautifulSoup(main_html, 'html.parser')
                    paragraphs = main_soup.find_all('p')
                    full_text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                except:
                    pass
            
            # 이미지 추출
            images = []
            for img in soup.find_all('img', src=True):
                src = img.get('src') or img.get('data-src')
                if src:
                    images.append(urljoin(url, src))
            
            return {
                "full_text": full_text[:10000] if full_text else "",  # 최대 10000자
                "images": images[:10],  # 최대 10개
                "status": "success" if full_text else "failed"
            }
            
        except Exception as e:
            return {"full_text": "", "images": [], "status": "failed"}
