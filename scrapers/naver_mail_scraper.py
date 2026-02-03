# Naver Mail Scraper
# 네이버 워크 메일 / 네이버 메일에서 이메일을 수집하여 뉴스 파이프라인에 통합

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Optional
import os
import sys
import re
from bs4 import BeautifulSoup

# 상위 디렉토리의 keywords 모듈 임포트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from keywords import classify_article

try:
    from .base_scraper import BaseScraper, NewsArticle
except ImportError:
    from base_scraper import BaseScraper, NewsArticle


class NaverMailScraper(BaseScraper):
    """
    네이버 워크 메일 / 네이버 메일 스크래퍼
    
    IMAP 프로토콜을 사용하여 이메일을 수집합니다.
    
    연결 설정:
    - 네이버 워크: imap.worksmobile.com:993 (SSL)
    - 일반 네이버: imap.naver.com:993 (SSL)
    
    환경변수:
    - NAVER_MAIL_EMAIL: 이메일 주소
    - NAVER_MAIL_PASSWORD: 비밀번호 (앱 비밀번호 권장)
    - NAVER_MAIL_SERVER: IMAP 서버 (기본값: imap.worksmobile.com)
    """
    
    # 기본 IMAP 설정
    DEFAULT_IMAP_SERVER = "imap.worksmobile.com"
    IMAP_PORT = 993
    
    def __init__(self, 
                 email_address: str = None, 
                 password: str = None,
                 imap_server: str = None):
        """
        스크래퍼 초기화
        
        Args:
            email_address: 이메일 주소 (없으면 환경변수에서 로드)
            password: 비밀번호 (없으면 환경변수에서 로드)
            imap_server: IMAP 서버 주소 (없으면 환경변수에서 로드)
        """
        self.email_address = email_address or os.getenv("NAVER_MAIL_EMAIL")
        self.password = password or os.getenv("NAVER_MAIL_PASSWORD")
        self.imap_server = imap_server or os.getenv("NAVER_MAIL_SERVER", self.DEFAULT_IMAP_SERVER)
        self.connection = None
        
    @property
    def source_name(self) -> str:
        return "Naver Mail"
    
    @property
    def base_url(self) -> str:
        return f"imaps://{self.imap_server}"
    
    def _get_days_back(self) -> int:
        """요일에 따른 수집 기간 결정"""
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return 3  # 주말 포함
        return 1  # 평일 1일
    
    def connect(self) -> bool:
        """IMAP 서버에 연결"""
        try:
            if not self.email_address or not self.password:
                print("[Naver Mail] Error: Email credentials not configured")
                print("[Naver Mail] Set NAVER_MAIL_EMAIL and NAVER_MAIL_PASSWORD in .env")
                return False
            
            print(f"[Naver Mail] Connecting to {self.imap_server}:{self.IMAP_PORT}...")
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.IMAP_PORT)
            self.connection.login(self.email_address, self.password)
            print(f"[Naver Mail] Connected successfully as {self.email_address}")
            return True
            
        except imaplib.IMAP4.error as e:
            print(f"[Naver Mail] Authentication failed: {e}")
            return False
        except Exception as e:
            print(f"[Naver Mail] Connection error: {e}")
            return False
    
    def disconnect(self):
        """IMAP 연결 종료"""
        if self.connection:
            try:
                self.connection.logout()
                print("[Naver Mail] Disconnected")
            except:
                pass
            self.connection = None
    
    def fetch_news(self, 
                   query: str = None, 
                   days_back: int = None,
                   folder: str = "INBOX",
                   sender_filter: str = None) -> List[NewsArticle]:
        """
        이메일 수집
        
        Args:
            query: 키워드 필터 (선택)
            days_back: 수집 기간 (일수, None이면 자동 계산)
            folder: 메일 폴더 (기본값: INBOX)
            sender_filter: 발신자 필터 (선택, 예: "@newsletter.com")
            
        Returns:
            NewsArticle 리스트
        """
        if days_back is None:
            days_back = self._get_days_back()
            
        cutoff_date = datetime.now() - timedelta(days=days_back)
        print(f"[Naver Mail] Days back: {days_back} (cutoff: {cutoff_date.strftime('%Y-%m-%d')})")
        
        articles = []
        
        # 연결
        if not self.connect():
            return articles
        
        try:
            # 폴더 선택
            status, messages = self.connection.select(folder)
            if status != "OK":
                print(f"[Naver Mail] Failed to select folder: {folder}")
                return articles
            
            # 날짜 기반 검색
            date_str = cutoff_date.strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{date_str}")'
            
            if sender_filter:
                search_criteria = f'(SINCE "{date_str}" FROM "{sender_filter}")'
            
            print(f"[Naver Mail] Searching with criteria: {search_criteria}")
            
            status, message_ids = self.connection.search(None, search_criteria)
            if status != "OK":
                print("[Naver Mail] Search failed")
                return articles
            
            email_ids = message_ids[0].split()
            print(f"[Naver Mail] Found {len(email_ids)} emails")
            
            # 최신 이메일부터 처리 (최대 50개)
            for email_id in reversed(email_ids[-50:]):
                try:
                    article = self._parse_email(email_id, query)
                    if article:
                        articles.append(article)
                except Exception as e:
                    print(f"[Naver Mail] Error parsing email {email_id}: {e}")
                    continue
            
            print(f"[Naver Mail] Total collected: {len(articles)} articles")
            
        except Exception as e:
            print(f"[Naver Mail] Error fetching emails: {e}")
        finally:
            self.disconnect()
        
        return articles
    
    def _parse_email(self, email_id: bytes, query: str = None) -> Optional[NewsArticle]:
        """개별 이메일 파싱"""
        status, msg_data = self.connection.fetch(email_id, "(RFC822)")
        if status != "OK":
            return None
        
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # 제목 디코딩
        subject = self._decode_header(msg["Subject"])
        if not subject:
            return None
        
        # 발신자
        sender = self._decode_header(msg["From"])
        
        # 날짜 파싱
        date_str = msg["Date"]
        published = self._parse_date(date_str)
        
        # 본문 추출
        body = self._extract_body(msg)
        if not body:
            return None
        
        # 키워드 필터링
        if query:
            if query.lower() not in f"{subject} {body}".lower():
                return None
        
        # 분류
        classifications, matched_keywords = classify_article(subject, body[:500])
        
        # 분류가 없으면 "이메일 뉴스레터"로 기본 분류
        if not classifications:
            classifications = ["이메일 뉴스레터"]
            matched_keywords = []
        
        # 요약 생성 (본문 첫 200자)
        summary = body[:200].strip()
        if len(body) > 200:
            summary += "..."
        
        # 고유 링크 생성 (이메일은 URL이 없으므로 message-id 사용)
        message_id = msg["Message-ID"] or f"email_{email_id.decode()}"
        link = f"mailto:{sender}?subject={subject[:50]}"
        
        return NewsArticle(
            title=f"[Email] {subject}",
            link=link,
            published=published,
            source=f"Naver Mail ({sender})",
            summary=summary,
            full_text=body[:5000],  # 최대 5000자
            images=[],
            scrape_status="success",
            classifications=classifications,
            matched_keywords=matched_keywords[:10]
        )
    
    def _decode_header(self, header: str) -> str:
        """이메일 헤더 디코딩"""
        if not header:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(str(part))
        
        return ' '.join(decoded_parts).strip()
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """이메일 본문 추출"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # 첨부파일 제외
                if "attachment" in content_disposition:
                    continue
                
                # 텍스트 본문 추출
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        break
                elif content_type == "text/html" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='replace')
                        body = self._html_to_text(html_body)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                content_type = msg.get_content_type()
                
                if content_type == "text/html":
                    body = self._html_to_text(payload.decode(charset, errors='replace'))
                else:
                    body = payload.decode(charset, errors='replace')
        
        return body.strip()
    
    def _html_to_text(self, html: str) -> str:
        """HTML을 텍스트로 변환"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 스크립트, 스타일 태그 제거
            for tag in soup.find_all(['script', 'style', 'head']):
                tag.decompose()
            
            # 텍스트 추출
            text = soup.get_text(separator='\n', strip=True)
            
            # 연속 공백/줄바꿈 정리
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'[ \t]+', ' ', text)
            
            return text.strip()
        except:
            return html
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """이메일 날짜 파싱"""
        if not date_str:
            return None
        
        try:
            # email.utils 사용
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).replace(tzinfo=None)
        except:
            pass
        
        # 수동 파싱 시도
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.replace(tzinfo=None)
            except:
                continue
        
        return None
    
    def list_folders(self) -> List[str]:
        """사용 가능한 메일 폴더 목록 조회"""
        if not self.connect():
            return []
        
        try:
            status, folders = self.connection.list()
            if status == "OK":
                folder_list = []
                for folder in folders:
                    # 폴더 이름 파싱
                    folder_str = folder.decode() if isinstance(folder, bytes) else str(folder)
                    match = re.search(r'"([^"]+)"$', folder_str)
                    if match:
                        folder_list.append(match.group(1))
                return folder_list
        except Exception as e:
            print(f"[Naver Mail] Error listing folders: {e}")
        finally:
            self.disconnect()
        
        return []


# 독립 실행 테스트
if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    
    # .env 파일 로드
    env_path = os.path.join(PROJECT_ROOT, 'config', '.env')
    load_dotenv(env_path)
    
    parser = argparse.ArgumentParser(description="Naver Mail Scraper")
    parser.add_argument("--days", type=int, default=None,
                       help="Days back (default: auto - 1 day or 3 on Monday)")
    parser.add_argument("--sender", type=str, default=None,
                       help="Filter by sender email")
    parser.add_argument("--folder", type=str, default="INBOX",
                       help="Mail folder to search (default: INBOX)")
    parser.add_argument("--query", type=str, default=None,
                       help="Keyword filter")
    parser.add_argument("--list-folders", action="store_true",
                       help="List available mail folders")
    args = parser.parse_args()
    
    scraper = NaverMailScraper()
    
    print("=" * 60)
    print("Naver Mail Scraper - 이메일 뉴스레터 수집")
    print("=" * 60)
    
    if args.list_folders:
        print("\n[Folders]")
        for folder in scraper.list_folders():
            print(f"  - {folder}")
    else:
        articles = scraper.fetch_news(
            query=args.query,
            days_back=args.days,
            folder=args.folder,
            sender_filter=args.sender
        )
        
        print(f"\nTotal collected: {len(articles)} articles\n")
        
        for i, article in enumerate(articles[:10], 1):
            date_str = article.published.strftime('%Y-%m-%d %H:%M') if article.published else 'N/A'
            print(f"{i}. [{date_str}] {article.title[:70]}...")
            print(f"   Source: {article.source}")
            print(f"   Classifications: {', '.join(article.classifications)}")
            if article.matched_keywords:
                print(f"   Keywords: {', '.join(article.matched_keywords[:5])}")
            print()
