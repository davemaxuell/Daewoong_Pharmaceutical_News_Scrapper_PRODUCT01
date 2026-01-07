# AI 요약 프로그램

import sys
import io
import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# API 키 로드
load_dotenv()


def get_openai_client() -> OpenAI:
    """
    OpenAI API 클라이언트 초기화
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "your_openai_api_key_here":
        raise ValueError(
            "OpenAI API 키를 찾을 수 없습니다!\n"
            ".env 파일에 API 키를 추가하세요:\n"
            "OPENAI_API_KEY=your_actual_api_key"
        )
    
    return OpenAI(api_key=api_key)


def summarize_article(client: OpenAI, title: str, content: str, images: list = None, model: str = "gpt-4o") -> dict:
    """
    OpenAI API를 사용하여 단일 기사를 요약합니다 (선택적 이미지 분석 포함).
    
    Args:
        client: OpenAI 클라이언트 인스턴스
        title: 기사 제목
        content: 기사 본문 텍스트
        images: 분석할 이미지 URL 목록 (선택사항)
        model: 사용할 OpenAI 모델 (기본값: gpt-4o-mini)
    
    Returns:
        요약, 핵심 포인트, 업계 영향을 포함하는 딕셔너리
    """
    
    # 내용이 없거나 너무 짧으면 건너뜀
    if not content or len(content) < 100:
        return {
            "ai_summary": "기사 본문이 충분하지 않습니다.",
            "key_points": [],
            "industry_impact": "",
            "ai_categories": [],
            "ai_keywords": [],
            "target_teams": []
        }
    
    # 토큰 절약을 위해 긴 내용 자르기 (최대 5000자)
    max_content_length = 5000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "..."
    
    # 분석할 이미지가 있는지 확인
    has_images = images and len(images) > 0
    
    # 비용 관리를 위해 최대 5개 이미지로 제한
    if has_images:
        images = images[:5]
    
    # 분류 카테고리 목록
    categories = [
        "주요전문지 헤드라인",
        "대웅/관계사",
        "정책/행정",
        "AI",
        "업계/R&D",
        "제품",
        "시장/투자",
        "인력/교육"
    ]
    
    # 팀 라우팅 정의
    from team_definitions import get_team_prompt, get_team_list
    team_descriptions = get_team_prompt()
    team_list = get_team_list()
    
    system_prompt = f"""당신은 제약/바이오 산업 전문 뉴스 분석가입니다.

기사 본문과 이미지(제공된 경우)를 함께 분석하여 다음 형식으로 JSON 응답을 제공해주세요.
이미지가 있다면 기사 이해에 도움이 되는 시각적 정보를 요약에 통합하세요.

{{
    "summary": "기사의 핵심 내용을 2-3문장으로 요약",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
    "industry_impact": "업계에 미치는 영향을 1-2문장으로 설명",
    "categories": ["해당되는 카테고리들"],
    "keywords": ["기사에서 추출한 핵심 키워드 3-5개"],
    "target_teams": ["이 뉴스를 받아야 할 팀 1-2개"]
}}

분류 카테고리 옵션 (1개 이상 선택): {categories}

타겟 팀 옵션 (가장 관련 있는 1-2개 선택):
{team_descriptions}

반드시 유효한 JSON 형식으로만 응답하세요."""

    user_text = f"""다음 제약/바이오 뉴스 기사를 분석해주세요:

제목: {title}

본문:
{content}"""

    try:
        # 이미지 유무에 따라 메시지 내용 구성
        if has_images:
            # 텍스트와 이미지를 포함한 콘텐츠 리스트 생성
            user_content = [{"type": "text", "text": user_text}]
            
            for img_url in images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_url,
                        "detail": "low"
                    }
                })
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        else:
            # 텍스트만 있는 메시지
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        # 응답 파싱
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        return {
            "ai_summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "industry_impact": result.get("industry_impact", ""),
            "ai_categories": result.get("categories", []),
            "ai_keywords": result.get("keywords", []),
            "target_teams": result.get("target_teams", []),
            "tokens_used": response.usage.total_tokens
        }
        
    except json.JSONDecodeError as e:
        print(f"    [WARN] JSON 파싱 실패: {e}")
        return {
            "ai_summary": response.choices[0].message.content if response else "",
            "key_points": [],
            "industry_impact": "",
            "ai_categories": [],
            "ai_keywords": [],
            "target_teams": [],
            "error": "JSON 파싱 실패"
        }
    except Exception as e:
        error_str = str(e)
        # 이미지 관련 오류인 경우, 이미지 없이 재시도
        if has_images and ("invalid_image_url" in error_str or "Timeout" in error_str or "invalid_image_format" in error_str):
            print(f"    [WARN] 이미지 로드 실패, 텍스트만으로 재시도...")
            # 이미지 없이 재귀 호출
            return summarize_article(client, title, content, images=None, model=model)
        
        print(f"    [ERROR] OpenAI API 오류: {e}")
        return {
            "ai_summary": "",
            "key_points": [],
            "industry_impact": "",
            "ai_categories": [],
            "ai_keywords": [],
            "target_teams": [],
            "error": error_str
        }


def summarize_all_articles(input_json: str, output_json: str = None, model: str = "gpt-4o-mini"):
    print("[INFO] OpenAI 클라이언트 초기화 중...")
    client = get_openai_client()
    
    with open(input_json, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print("=" * 60)
    print("AI 뉴스 요약 설정")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"총 {len(articles)}개의 기사를 분석합니다.")
    print(f"모델: {model}")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    total_tokens = 0
    
    for i, article in enumerate(articles, 1):
        title = article.get("title", article.get("scraped_title", "Unknown"))
        content = article.get("full_text", "")
        images = article.get("images", [])  # 스크래핑된 기사에서 이미지 가져오기
        
        print(f"\n[{i}/{len(articles)}] 분석 중: {title[:50]}...")
        
        if article.get("scrape_status") != "success" or not content:
            print(f"    [SKIP] 기사 본문 없음")
            article["ai_analysis"] = {
                "ai_summary": "기사 본문을 가져올 수 없습니다.",
                "key_points": [],
                "industry_impact": "",
                "ai_categories": [],
                "ai_keywords": [],
                "target_teams": [],
                "error": "기사 본문 없음"
            }
            fail_count += 1
            continue
        
        # 이미지를 summarize_article에 전달하여 비전 분석 수행
        result = summarize_article(client, title, content, images=images, model=model)
        
        if result.get("error"):
            print(f"    [FAILED] {result.get('error')}")
            fail_count += 1
        else:
            success_count += 1
            tokens = result.get("tokens_used", 0)
            total_tokens += tokens
            print(f"    [SUCCESS] 요약 완료 (토큰: {tokens})")
            print(f"    {result.get('ai_summary', '')[:80]}...")
        
        article["ai_analysis"] = result
    
    if output_json is None:
        output_json = input_json.replace("content_", "summarized_")
        if output_json == input_json:
            output_json = input_json.replace(".json", "_summarized.json")
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    estimated_cost = (total_tokens / 1_000_000) * 0.30 
    print("\n" + "=" * 60)
    print(f"[DONE] AI 분석 완료!")
    print(f"  성공: {success_count}개")
    print(f"  실패: {fail_count}개")
    print(f"  총 토큰 사용: {total_tokens:,}")
    print(f"  예상 비용: ${estimated_cost:.4f}")
    print(f"  결과 저장: {output_json}")
    print("=" * 60)
    
    return articles


def summarize_single_url(url: str, model: str = "gpt-4o-mini") -> dict:
    from content_scraper import fetch_article_content
    
    print(f"URL 스크래핑: {url}")
    scraped = fetch_article_content(url)
    
    if not scraped["success"]:
        return {
            "success": False,
            "error": scraped.get("error", "Scraping failed"),
            "url": url
        }
    
    print(f"스크래핑 완료: {len(scraped['text'])}자")
    client = get_openai_client()
    summary = summarize_article(client, scraped["title"], scraped["text"], model)
    
    return {
        "success": True,
        "url": scraped["final_url"],
        "title": scraped["title"],
        "content": scraped["text"],
        "images": scraped["images"],
        "ai_analysis": summary
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI 뉴스 요약기")
    parser.add_argument("--input", "-i", help="입력 JSON 파일 (스크래핑된 기사)")
    parser.add_argument("--output", "-o", help="출력 JSON 파일 (선택사항)")
    parser.add_argument("--url", "-u", help="단일 URL 분석")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="OpenAI 모델 (default: gpt-4o-mini)")
    
    args = parser.parse_args()
    
    if args.url:
        result = summarize_single_url(args.url, args.model)
        print("\n" + "=" * 60)
        print("분석 결과:")
        print("=" * 60)
        if result["success"]:
            print(f"제목: {result['title']}")
            print(f"요약: {result['ai_analysis'].get('ai_summary', 'N/A')}")
            print(f"업계 영향: {result['ai_analysis'].get('industry_impact', 'N/A')}")
        else:
            print(f"오류: {result.get('error', 'Unknown error')}")
    
    elif args.input:
        summarize_all_articles(args.input, args.output, args.model)
    
    else:
        today = datetime.now().strftime('%Y%m%d')
        input_file = f"pharma_news_content_{today}.json"
        
        try:
            summarize_all_articles(input_file, model=args.model)
        except FileNotFoundError:
            print(f"[ERROR] 파일을 찾을 수 없습니다: {input_file}")
            print("먼저 content_scraper.py를 실행하세요.")
        except ValueError as e:
            print(f"[ERROR] {e}")
