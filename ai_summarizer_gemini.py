# AI 요약 프로그램 (Gemini 버전)
# Google Gemini API를 사용한 뉴스 요약
# Updated to use google-genai SDK

import sys
import io
import json
import os
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# API 키 로드
load_dotenv()

# 모델명 상수
MODEL_NAME = 'gemini-2.0-flash'


def get_gemini_client():
    """
    Gemini API 클라이언트 초기화
    Returns: genai.Client
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key or api_key.startswith("your_"):
        raise ValueError(
            "Gemini API 키를 찾을 수 없습니다!\n"
            ".env 파일에 API 키를 추가하세요:\n"
            "GEMINI_API_KEY=your_actual_api_key"
        )
    
    return genai.Client(api_key=api_key)


def summarize_article(client, title: str, content: str, images: list = None) -> dict:
    """
    Gemini API를 사용하여 단일 기사를 요약합니다.
    
    Args:
        client: Gemini Client 인스턴스
        title: 기사 제목
        content: 기사 본문 텍스트
        images: 이미지 URL 목록
    
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
    from team_definitions import get_team_prompt
    team_descriptions = get_team_prompt()
    
    prompt = f"""당신은 제약/바이오 산업 전문 뉴스 분석가입니다.

다음 제약/바이오 뉴스 기사를 분석하여 아래 형식의 JSON으로 응답해주세요.

기사 제목: {title}

기사 본문:
{content}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
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

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=800,
            )
        )
        
        # 응답 파싱
        result_text = response.text.strip()
        
        # JSON 블록 추출
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        return {
            "ai_summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "industry_impact": result.get("industry_impact", ""),
            "ai_categories": result.get("categories", []),
            "ai_keywords": result.get("keywords", []),
            "target_teams": result.get("target_teams", []),
            "model_used": MODEL_NAME
        }
        
    except json.JSONDecodeError as e:
        print(f"    [WARN] JSON 파싱 실패: {e}")
        return {
            "ai_summary": result_text[:200] if 'result_text' in locals() and result_text else "",
            "key_points": [],
            "industry_impact": "",
            "ai_categories": [],
            "ai_keywords": [],
            "target_teams": [],
            "error": "JSON 파싱 실패"
        }
    except Exception as e:
        print(f"    [ERROR] AI 요청 실패: {e}")
        return {
            "ai_summary": "",
            "key_points": [],
            "industry_impact": "",
            "ai_categories": [],
            "ai_keywords": [],
            "target_teams": [],
            "error": str(e)
        }


def analyze_pdf(client, pdf_url: str, title: str = "PDF Document") -> dict:
    """
    URL에서 PDF를 다운로드하고 Gemini에게 변경사항 분석을 요청합니다.
    """
    print(f"  [PDF Analysis] Downloading: {pdf_url}")
    try:
        import requests
        response = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
        pdf_data = response.content
        
        prompt = f"""당신은 제약 규제 전문가입니다.
다음 PDF 문서는 '{title}'입니다.
이 문서의 **주요 변경 사항**이나 **핵심 업데이트 내용**을 분석해 주세요.

다음 JSON 형식으로 응답하세요:
{{
    "summary": "문서의 핵심 목적과 주요 변경사항 요약 (3-4문장)",
    "key_changes": ["변경사항 1", "변경사항 2", "변경사항 3"],
    "implications": "제약 업계에 미치는 영향 및 대응 방안",
    "target_teams": ["관련 팀 (예: RA팀, 품질관리팀 등)"]
}}
"""
        
        gemini_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type='application/pdf'),
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1000,
            )
        )
        
        # 응답 파싱
        result_text = gemini_response.text.strip()
        
        # JSON 블록 추출
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
            
        return json.loads(result_text)

    except Exception as e:
        print(f"  [ERROR] PDF Analysis Failed: {e}")
        return {"error": str(e)}


def summarize_all_articles(input_json: str, output_json: str = None):
    print("[INFO] Gemini 클라이언트 초기화 중...")
    client = get_gemini_client()
    
    with open(input_json, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print("=" * 60)
    print("AI 뉴스 요약 (Gemini)")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"총 {len(articles)}개의 기사를 분석합니다.")
    print(f"모델: {MODEL_NAME}")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, article in enumerate(articles, 1):
        title = article.get("title", article.get("scraped_title", "Unknown"))
        content = article.get("full_text", "") or article.get("summary", "")
        images = article.get("images", [])
        
        print(f"\n[{i}/{len(articles)}] 분석 중: {title[:50]}...")
        
        # 본문이 없거나 너무 짧으면 스킵
        if not content or len(content) < 50:
            print(f"    [SKIP] 기사 본문 없음 또는 너무 짧음")
            article["ai_analysis"] = {
                "ai_summary": article.get("summary", "기사 본문을 가져올 수 없습니다."),
                "key_points": [],
                "industry_impact": "",
                "ai_categories": article.get("classifications", []),
                "ai_keywords": article.get("matched_keywords", []),
                "target_teams": [],
                "error": "기사 본문 없음"
            }
            fail_count += 1
            continue
        
        # client(model argument) passed here
        result = summarize_article(client, title, content, images=images)
        
        if result.get("error"):
            print(f"    [FAILED] {result.get('error')}")
            fail_count += 1
        else:
            success_count += 1
            print(f"    [SUCCESS] 요약 완료")
            print(f"    {result.get('ai_summary', '')[:80]}...")
        
        article["ai_analysis"] = result
    
    if output_json is None:
        output_json = input_json.replace("content_", "summarized_")
        if output_json == input_json:
            output_json = input_json.replace(".json", "_summarized.json")
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"[DONE] AI 분석 완료! (Gemini)")
    print(f"  성공: {success_count}개")
    print(f"  실패: {fail_count}개")
    print(f"  결과 저장: {output_json}")
    print("=" * 60)
    
    return articles


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI 뉴스 요약기 (Gemini)")
    parser.add_argument("--input", "-i", help="입력 JSON 파일 (스크래핑된 기사)")
    parser.add_argument("--output", "-o", help="출력 JSON 파일 (선택사항)")
    
    args = parser.parse_args()
    
    if args.input:
        summarize_all_articles(args.input, args.output)
    else:
        today = datetime.now().strftime('%Y%m%d')
        input_file = f"multi_source_content_{today}.json"
        
        try:
            summarize_all_articles(input_file)
        except FileNotFoundError:
            print(f"[ERROR] 파일을 찾을 수 없습니다: {input_file}")
            print("먼저 content_scraper.py를 실행하세요.")
        except ValueError as e:
            print(f"[ERROR] {e}")
