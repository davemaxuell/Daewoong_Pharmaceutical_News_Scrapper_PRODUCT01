# AI 요약 프로그램 (Gemini 버전)
# Google Gemini API를 사용한 뉴스 요약
# Updated to use google-genai SDK

import sys
import io
import json
import os
import re
from datetime import datetime

# 프로젝트 루트 설정 (src/ 상위 디렉토리)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from google import genai
from google.genai import types

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.env_config import first_env, load_project_env

# API 키 로드 (.env 또는 config/.env)
load_project_env()

# 모델명 (.env 우선)
MODEL_NAME = first_env("GEMINI_MODEL_NAME", "GOOGLE_MODEL_NAME", default="gemini-2.5-flash")

ARTICLE_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "key_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "industry_impact": {"type": "STRING"},
        "categories": {"type": "ARRAY", "items": {"type": "STRING"}},
        "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
        "target_teams": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["summary", "key_points", "industry_impact", "categories", "keywords", "target_teams"],
}

PDF_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "key_changes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "implications": {"type": "STRING"},
        "target_teams": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["summary", "key_changes", "implications", "target_teams"],
}


def _fallback_summary_text(title: str, content: str, limit: int = 280) -> str:
    """Create a readable local fallback summary when AI output is unavailable."""
    cleaned = " ".join((content or "").split())
    if not cleaned:
        return title or "요약을 생성할 수 없습니다."
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _clean_summary_text(value: str, title: str, content: str, limit: int = 280) -> str:
    text = (value or "").strip()
    if not text:
        return _fallback_summary_text(title, content, limit=limit)

    if "```" in text:
        text = text.replace("```text", "").replace("```", "").strip()

    text = re.sub(r"^\s*(summary|요약)\s*[:：-]\s*", "", text, flags=re.IGNORECASE)
    text = text.strip(" \t\r\n\"'")
    text = re.sub(r"\s+", " ", text)

    if len(text) <= 10:
        return _fallback_summary_text(title, content, limit=limit)

    if len(text) > limit:
        text = text[:limit].rstrip() + "..."

    return text


def _extract_json_payload(result_text: str) -> dict:
    """Best-effort JSON extraction for Gemini responses."""
    text = (result_text or "").strip()
    if not text:
        raise json.JSONDecodeError("Empty response", text, 0)

    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    text = re.sub(r"[\x00-\x08\x0b-\x1f]", " ", text)
    return json.loads(text)


def _clean_json_string(value: str) -> str:
    if value is None:
        return ""
    cleaned = str(value)
    cleaned = cleaned.replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" \t\r\n\"',")


def _extract_string_field(text: str, field_name: str) -> str:
    pattern = rf'"{re.escape(field_name)}"\s*:\s*"((?:[^"\\]|\\.)*)'
    match = re.search(pattern, text, re.S)
    if not match:
        return ""
    return _clean_json_string(match.group(1))


def _extract_array_field(text: str, field_name: str) -> list[str]:
    pattern = rf'"{re.escape(field_name)}"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, text, re.S)
    if not match:
        return []

    values = []
    for item in re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1)):
        cleaned = _clean_json_string(item)
        if cleaned:
            values.append(cleaned)
    return values


def _salvage_partial_response(result_text: str, title: str, content: str) -> dict | None:
    """Recover useful fields from truncated JSON-like model output."""
    text = (result_text or "").strip()
    if not text:
        return None

    summary = _extract_string_field(text, "summary")
    if not summary:
        return None

    return {
        "ai_summary": summary,
        "key_points": _extract_array_field(text, "key_points"),
        "industry_impact": _extract_string_field(text, "industry_impact"),
        "ai_categories": _extract_array_field(text, "categories"),
        "ai_keywords": [],
        "target_teams": _extract_array_field(text, "target_teams"),
        "model_used": MODEL_NAME,
        "parse_salvaged": True,
    }


def get_gemini_client():
    """
    Gemini API 클라이언트 초기화
    Returns: genai.Client
    """
    api_key = first_env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    
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
    
    prompt = f"""당신은 제약/바이오 산업 전문 뉴스 분석가입니다.

아래 기사를 한국어로 2~3문장으로만 깔끔하게 요약하세요.
- JSON, 마크다운, 따옴표, 제목 라벨을 쓰지 마세요.
- 이메일 본문에 바로 넣을 수 있도록 자연스러운 문장만 출력하세요.
- 핵심 사실과 업계 의미를 짧게 포함하세요.

기사 제목: {title}

기사 본문:
{content}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )
        )

        summary_text = _clean_summary_text(getattr(response, "text", ""), title, content)

        return {
            "ai_summary": summary_text,
            "key_points": [],
            "industry_impact": "",
            "ai_categories": [],
            "ai_keywords": [],  # 스크래퍼의 규칙 기반 matched_keywords로 채워짐
            "target_teams": [],
            "model_used": MODEL_NAME
        }
    except Exception as e:
        print(f"    [ERROR] AI 요청 실패: {e}")
        return {
            "ai_summary": _fallback_summary_text(title, content),
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
                response_mime_type="application/json",
                response_schema=PDF_RESPONSE_SCHEMA,
            )
        )
        
        # 응답 파싱
        if getattr(gemini_response, "parsed", None):
            return gemini_response.parsed
        return _extract_json_payload(gemini_response.text.strip())

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
        
        # 규칙 기반 키워드만 사용 (스크래퍼의 matched_keywords)
        # AI 생성 키워드는 사용하지 않음
        article["ai_analysis"]["ai_keywords"] = article.get("matched_keywords", [])
    
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
