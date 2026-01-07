# [PARSING] 제약 뉴스 수집 - 메인 실행 파일

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from datetime import datetime
import time
import json
from keywords import KEYWORDS
from scrapers import AVAILABLE_SCRAPERS, NewsArticle
from logger import log_execution


def get_days_back() -> int:
    """
    오늘 요일에 따라 수집할 기간 계산
    - 월요일(0): 금요일부터 = 3일
    - 화~일: 전날부터 = 1일
    """
    today = datetime.now()
    weekday = today.weekday()
    
    if weekday == 0:
        days_back = 3
        print("[INFO] 오늘은 월요일입니다. 금요일부터의 뉴스를 수집합니다 (3일간).")
    else:
        days_back = 1
        print(f"[INFO] 어제부터의 뉴스를 수집합니다 (1일간).")
    
    return days_back


def get_all_keywords() -> list[str]:
    """KEYWORDS 딕셔너리에서 모든 키워드 추출"""
    all_keywords = set()
    for category, keywords in KEYWORDS.items():
        all_keywords.update(keywords)
    return list(all_keywords)


def main():
    print("=" * 60)
    print("제약 뉴스 에이전트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 사용 가능한 스크래퍼 출력
    scraper_names = [s().source_name for s in AVAILABLE_SCRAPERS]
    print(f"\n[INFO] 사용 가능한 뉴스 소스: {', '.join(scraper_names)}")
    print(f"[INFO] 분류 카테고리: {list(KEYWORDS.keys())}")
    
    all_articles = []
    
    # 한국어 검색 키워드 (국내 뉴스 소스용)
    korean_keywords = [
        "제약", "의약품", "신약", "바이오",
        "바이오시밀러", "임상시험", "FDA 승인",
        "항암제", "면역항암제", "세포치료제",
        "제약 주가", "바이오 투자", "기술이전",
        "디지털헬스케어", "AI 신약"
    ]
    
    # 영문 검색 키워드 (국제 뉴스 소스용)
    english_keywords = [
        "pharmaceutical", "drug approval", "GMP",
        "clinical trial", "FDA", "EMA", "biosimilar",
        "cell therapy", "gene therapy", "ATMP",
        "ICH guideline", "regulatory"
    ]
    
    # 국제 소스 목록 (영어 키워드 사용 또는 RSS 피드)
    international_sources = ["GMP Journal"]
    
    # RSS 전용 소스 (키워드 검색 없이 전체 피드 수집)
    rss_only_sources = ["ICH", "EudraLex"]
    
    days_back = get_days_back()
    
    # 모든 스크래퍼에서 뉴스 수집
    for ScraperClass in AVAILABLE_SCRAPERS:
        scraper = ScraperClass()
        print(f"\n{'='*40}")
        print(f"<{scraper.source_name}에서 기사 수집 시작>")
        print(f"{'='*40}")
        
        # RSS 전용 소스는 키워드 없이 한 번만 수집 (같은 days_back 사용)
        if scraper.source_name in rss_only_sources:
            articles = scraper.fetch_news(days_back=days_back)
            all_articles.extend(articles)
        # 국제 소스는 영어 키워드 사용
        elif scraper.source_name in international_sources:
            for keyword in english_keywords:
                articles = scraper.fetch_news(keyword, days_back=days_back)
                all_articles.extend(articles)
                time.sleep(0.5)
        # 국내 소스는 한국어 키워드 사용
        else:
            for keyword in korean_keywords:
                articles = scraper.fetch_news(keyword, days_back=days_back)
                all_articles.extend(articles)
                time.sleep(0.5)
    
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
    
    # 소스별 통계
    source_stats = {}
    for article in unique_articles:
        source_stats[article.source] = source_stats.get(article.source, 0) + 1
    
    # 결과 출력
    print(f"\n{'='*60}")
    print(f"[SUCCESS] 총 {len(unique_articles)}개의 뉴스를 수집했습니다.")
    print("=" * 60)
    
    if source_stats:
        print("\n[소스별 통계]")
        for src, count in sorted(source_stats.items(), key=lambda x: -x[1]):
            print(f"  - {src}: {count}개")
    
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
    output_data = [article.to_dict() for article in unique_articles]
    
    output_file = f"pharma_news_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SUCCESS] 결과를 {output_file}에 저장했습니다.")
    
    # 실행 결과 로깅
    log_execution(
        total_articles=len(unique_articles),
        source_stats=source_stats,
        classification_stats=classification_stats,
        output_file=output_file
    )
    print(f"[LOG] 실행 기록이 logs/ 폴더에 저장되었습니다.")
    
    return unique_articles, source_stats, classification_stats, output_file


if __name__ == "__main__":
    articles = main()
