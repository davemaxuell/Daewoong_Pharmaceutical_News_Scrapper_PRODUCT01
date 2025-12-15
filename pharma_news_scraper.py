# [PARSING] RSS 뉴스 최근 뉴스 수집

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import feedparser
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import time
import json
from keywords import KEYWORDS, classify_article



@dataclass
class NewsArticle:
    """수집할 기사 데이터 클래스"""
    title: str
    link: str
    published: Optional[datetime]
    source: str
    summary: Optional[str] = None
    classifications: list = field(default_factory=list)  # 매칭된 분류
    matched_keywords: list = field(default_factory=list)  # 매칭된 키워드


def get_days_back() -> int:
    """
    오늘 요일에 따라 수집할 기간 계산
    - 월요일(0): 금요일부터 = 3일
    - 화~일: 전날부터 = 1일
    """
    today = datetime.now()
    weekday = today.weekday()  # 0=월요일, 6=일요일
    
    if weekday == 0:  # 월요일
        days_back = 3  # 금요일부터 (토, 일 포함)
        print("[INFO] 오늘은 월요일입니다. 금요일부터의 뉴스를 수집합니다 (3일간).")
    else:
        days_back = 1  # 어제부터
        print(f"[INFO] 어제부터의 뉴스를 수집합니다 (1일간).")
    
    return days_back


def get_all_keywords() -> list[str]:
    """
    KEYWORDS 딕셔너리에서 모든 키워드 추출 (중복 제거)
    """
    all_keywords = set()
    for category, keywords in KEYWORDS.items():
        all_keywords.update(keywords)
    return list(all_keywords)


def fetch_google_news_rss(query: str, days_back: int = 1) -> list[NewsArticle]:
    """
    Google News RSS 뉴스 수집
    """
    from urllib.parse import quote
    
    # URL 인코딩 적용
    encoded_query = quote(query)
    
    # Google News RSS URL (한국에 한정된 도메인)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    print(f"\n[PROCESS] Google News RSS로 기사 수집, 검색어: '{query}'")
    feed = feedparser.parse(url)
    
    if feed.bozo:
        print(f"\n[WARNING] Feed parsing issue - {feed.bozo_exception}")
    
    articles = []
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    for entry in feed.entries:
        try:
            # Parse the published date
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            else:
                published = None
            
            # Filter for recent articles only
            if published and published >= cutoff_date:
                # 분류 및 키워드 매칭
                title = entry.title
                summary = entry.get('summary', '') or ''
                classifications, matched_keywords = classify_article(title, summary)
                
                article = NewsArticle(
                    title=title,
                    link=entry.link,
                    published=published,
                    source=entry.get('source', {}).get('title', None),
                    summary=summary,
                    classifications=classifications,
                    matched_keywords=matched_keywords
                )
                articles.append(article)
        except Exception as e:
            continue
    
    print(f"\n[SUCCESS] {len(articles)}개의 뉴스를 수집했습니다.")
    return articles


def main():
    print("=" * 60)
    print("제약 뉴스 에이전트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 키워드 목록 출력
    all_keywords = get_all_keywords()
    print(f"\n[INFO] 총 {len(all_keywords)}개의 키워드로 검색합니다.")
    print(f"[INFO] 분류 카테고리: {list(KEYWORDS.keys())}")
    
    all_articles = []
    
    # 기본 검색 키워드 (확장됨)
    base_keywords = [
        # 핵심 키워드
        "제약", "의약품", "신약", "바이오",
        # 주요 분야
        "바이오시밀러", "임상시험", "FDA 승인",
        "항암제", "면역항암제", "세포치료제",
        # 산업/시장
        "제약 주가", "바이오 투자", "기술이전",
        # 헬스케어
        "디지털헬스케어", "AI 신약"
    ]
    
    # 월요일이면 금요일부터 수집 (주말 커버)
    days_back = get_days_back()
    
    print("\n<Google News RSS로 기사 수집 시작>\n")
    for keyword in base_keywords:
        articles = fetch_google_news_rss(keyword, days_back=days_back)
        all_articles.extend(articles)
        time.sleep(0.5)  # Be polite to Google
    
    # 중복 제거
    seen_links = set()
    unique_articles = []
    for article in all_articles:
        if article.link not in seen_links:
            seen_links.add(article.link)
            unique_articles.append(article)
    
    # 날짜로 정렬
    unique_articles.sort(
        key=lambda x: x.published if x.published else datetime.min,
        reverse=True
    )
    
    # 분류별 통계
    classification_stats = {}
    for article in unique_articles:
        for cls in article.classifications:
            classification_stats[cls] = classification_stats.get(cls, 0) + 1
    
    # 결과 출력
    print(f"\n[SUCCESS] {len(unique_articles)}개의 뉴스를 수집했습니다.")
    print("=" * 60)
    
    if classification_stats:
        print("\n[분류별 통계]")
        for cls, count in sorted(classification_stats.items(), key=lambda x: -x[1]):
            print(f"  - {cls}: {count}개")
    
    print("\n[PROCESS] 뉴스 출력")
    for i, article in enumerate(unique_articles, 1):
        date_str = article.published.strftime("%Y-%m-%d %H:%M") if article.published else "Unknown"
        print(f"\n[{i}] {article.title}")
        print(f"Date: {date_str} | Source: {article.source}")
        if article.classifications:
            print(f"분류: {', '.join(article.classifications)}")
            print(f"키워드: {', '.join(article.matched_keywords)}")
        print(f"Link: {article.link}")
    
    # JSON 파일로 저장
    output_data = []
    for article in unique_articles:
        output_data.append({
            "title": article.title,
            "link": article.link,
            "published": article.published.isoformat() if article.published else None,
            "source": article.source,
            "summary": article.summary,
            "classifications": article.classifications,
            "matched_keywords": article.matched_keywords
        })
    
    output_file = f"pharma_news_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SUCCESS] 결과를 {output_file}에 저장했습니다.")
    
    return unique_articles

if __name__ == "__main__":
    articles = main()
