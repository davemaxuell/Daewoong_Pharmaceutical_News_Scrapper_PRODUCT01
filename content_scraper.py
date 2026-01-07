# [SCRAPING] 기사 본문 및 이미지 수집
# 수집된 뉴스 링크에서 기사 내용을 스크래핑

import sys
import io
import json
import requests
from readability import Document
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def resolve_google_news_url(url: str) -> str:
    """
    Google News RSS 링크에서 실제 기사 URL 추출
    googlenewsdecoder 패키지를 사용하여 인코딩된 URL 디코딩
    """
    try:
        # Google News RSS 링크인 경우
        if "news.google.com" in url:
            from googlenewsdecoder import new_decoderv1
            decoded = new_decoderv1(url)
            if decoded.get("status"):
                return decoded.get("decoded_url", url)
        return url
    except Exception as e:
        print(f"    [WARN] URL 디코딩 실패: {e}")
        return url


def fetch_article_content(url: str) -> dict:
    """
    기사 URL에서 본문 텍스트와 이미지를 추출
    """
    try:
        # Step 0: Google News URL이면 실제 URL로 리다이렉트
        actual_url = resolve_google_news_url(url)
        
        # 여전히 Google News URL이면 (리다이렉트 실패) 건너뛰기
        if "news.google.com" in actual_url:
            return {"success": False, "error": "Could not resolve Google News redirect", "final_url": url}
        
        # Step 1: 실제 기사 페이지 요청
        resp = requests.get(actual_url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        
        # 인코딩 명시적으로 UTF-8로 설정 (한글 깨짐 방지)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        
        final_url = resp.url
        html = resp.text
        
        # Step 2: Readability로 메인 컨텐츠 추출
        doc = Document(html)
        main_html = doc.summary()
        title = doc.title()
        
        # Step 3: BeautifulSoup으로 텍스트 및 이미지 추출
        soup = BeautifulSoup(main_html, "lxml")
        
        # 본문 텍스트 추출
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        
        # 이미지 URL 추출
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                absolute_url = urljoin(final_url, src)
                images.append(absolute_url)
        
        # 원본 HTML에서도 이미지 추출 (readability가 놓친 이미지)
        original_soup = BeautifulSoup(html, "lxml")
        article_section = original_soup.find("article") or original_soup.find(class_=["article", "content", "post-content"])
        if article_section:
            for img in article_section.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    absolute_url = urljoin(final_url, src)
                    if absolute_url not in images:
                        images.append(absolute_url)
        
        return {
            "success": True,
            "final_url": final_url,
            "title": title.replace('\ufeff', '').strip(),  # BOM 제거
            "text": text.replace('\ufeff', '').strip(),    # BOM 제거
            "images": images
        }
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout", "final_url": url}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e), "final_url": url}
    except Exception as e:
        return {"success": False, "error": str(e), "final_url": url}


def scrape_all_articles(input_json: str, output_json: str = None):
    """
    JSON 파일에서 기사 링크를 읽고 모든 기사의 내용을 스크래핑
    """
    # JSON 파일 로드
    if not os.path.exists(input_json):
        # 현재 경로에 없으면 스크립트 경로에서 시도
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, input_json)
        if os.path.exists(alt_path):
            input_json = alt_path
        else:
            print(f"[ERROR] Input file not found: {input_json}")
            # Try to list available files to help debug
            print(f"Current dir: {os.getcwd()}")
            print(f"Script dir: {script_dir}")
            return []

    with open(input_json, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print("=" * 60)
    print("기사 본문 스크래퍼")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"총 {len(articles)}개의 기사를 스크래핑합니다.")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, article in enumerate(articles, 1):
        url = article.get("link", "")
        original_title = article.get("title", "Unknown")
        
        print(f"\n[{i}/{len(articles)}] 스크래핑 중: {original_title[:50]}...")
        
        result = fetch_article_content(url)
        
        if result["success"]:
            # 기사 데이터 업데이트
            article["final_url"] = result["final_url"]
            article["full_text"] = result["text"]
            article["images"] = result["images"]
            article["scraped_title"] = result["title"]
            article["scrape_status"] = "success"
            
            # 기존 분류 유지 (pharma_news_scraper.py에서 분류된 결과 그대로 사용)
            # classifications와 matched_keywords는 입력 JSON에서 그대로 보존됨
            
            success_count += 1
            cls_count = len(article.get('classifications', []))
            cls_info = f", 분류: {cls_count}개" if cls_count > 0 else ""
            print(f"    [SUCCESS] 본문: {len(result['text'])}자, 이미지: {len(result['images'])}개{cls_info}")
        else:
            article["final_url"] = result.get("final_url", url)
            article["full_text"] = ""
            article["images"] = []
            article["scrape_status"] = "failed"
            article["scrape_error"] = result.get("error", "Unknown error")
            fail_count += 1
            print(f"    [FAILED] {result.get('error', 'Unknown error')}")
        
        # 서버에 부담을 주지 않기 위해 딜레이
        time.sleep(1)
    
    # 결과 저장
    if output_json is None:
        output_json = input_json.replace("pharma_news_", "pharma_news_content_")
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"[DONE] 스크래핑 완료!")
    print(f"  성공: {success_count}개")
    print(f"  실패: {fail_count}개")
    print(f"  결과 저장: {output_json}")
    print("=" * 60)
    
    return articles


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="기사 본문 스크래퍼")
    parser.add_argument("-i", "--input", help="입력 JSON 파일")
    parser.add_argument("-o", "--output", help="출력 JSON 파일")
    
    args = parser.parse_args()
    
    # 입력 파일 결정
    if args.input:
        input_file = args.input
    else:
        today = datetime.now().strftime('%Y%m%d')
        input_file = f"pharma_news_{today}.json"
    
    try:
        scraped_articles = scrape_all_articles(input_file, args.output)
    except FileNotFoundError:
        print(f"[ERROR] 파일을 찾을 수 없습니다: {input_file}")
        print("먼저 뉴스 스크래퍼를 실행하세요.")
