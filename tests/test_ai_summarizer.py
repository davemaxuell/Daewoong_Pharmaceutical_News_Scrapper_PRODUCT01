#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Summarizer (Gemini) 테스트
API 키 유효성, 토큰 크레딧, 요약 기능을 확인합니다.

Usage:
  python tests/test_ai_summarizer.py              # 기본 테스트 (API 연결 + 샘플 요약)
  python tests/test_ai_summarizer.py --quick       # API 연결만 확인
  python tests/test_ai_summarizer.py --file FILE   # 실제 JSON 파일로 1건 요약 테스트
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))


def test_api_connection():
    """Gemini API 연결 테스트"""
    print("\n[1] Testing Gemini API connection...")

    try:
        from src.ai_summarizer_gemini import get_gemini_client, MODEL_NAME
        client = get_gemini_client()
        print(f"  -> API client initialized")
        print(f"  -> Model: {MODEL_NAME}")
        return client
    except ValueError as e:
        print(f"  -> [FAIL] API key missing: {e}")
        return None
    except Exception as e:
        print(f"  -> [FAIL] Connection error: {e}")
        return None


def test_simple_request(client):
    """간단한 API 요청 테스트 (토큰 크레딧 확인)"""
    print("\n[2] Testing simple API request (token credit check)...")

    try:
        from src.ai_summarizer_gemini import MODEL_NAME
        from google.genai import types

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Reply with exactly: OK",
            config=types.GenerateContentConfig(
                max_output_tokens=10,
                temperature=0
            )
        )

        result = response.text.strip()
        print(f"  -> Response: {result}")

        if "OK" in result.upper():
            print("  -> [PASS] API is working, tokens available")
            return True
        else:
            print(f"  -> [WARN] Unexpected response: {result}")
            return True

    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "rate" in error_msg or "429" in error_msg:
            print(f"  -> [FAIL] Token quota exceeded: {e}")
        elif "401" in error_msg or "403" in error_msg or "key" in error_msg:
            print(f"  -> [FAIL] API key invalid: {e}")
        else:
            print(f"  -> [FAIL] API error: {e}")
        return False


def test_summarize_sample(client):
    """샘플 기사 요약 테스트"""
    print("\n[3] Testing article summarization...")

    sample_title = "FDA Issues Warning Letter to Pharmaceutical Manufacturer for GMP Violations"
    sample_content = """
    The FDA issued a warning letter to a pharmaceutical company after inspections
    revealed significant violations of current good manufacturing practice (cGMP)
    regulations. The violations included inadequate cleaning validation procedures,
    failure to establish adequate written procedures for production and process controls,
    and insufficient investigation of out-of-specification results. The company has
    15 business days to respond with a corrective action plan.
    """

    try:
        from src.ai_summarizer_gemini import summarize_article

        start_time = datetime.now()
        result = summarize_article(client, sample_title, sample_content)
        elapsed = (datetime.now() - start_time).total_seconds()

        if result and result.get("summary"):
            print(f"  -> Summary: {result['summary'][:100]}...")
            print(f"  -> Completed in {elapsed:.2f}s")
            print("  -> [PASS] Summarization working")
            return True
        else:
            print(f"  -> [WARN] Empty result: {result}")
            return False

    except Exception as e:
        print(f"  -> [FAIL] Summarization error: {e}")
        return False


def test_with_file(client, file_path):
    """실제 JSON 파일에서 1건 요약 테스트"""
    print(f"\n[4] Testing with real file: {os.path.basename(file_path)}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)

        if not articles:
            print("  -> [WARN] Empty file")
            return False

        # Find first article with content
        test_article = None
        for article in articles:
            if article.get("title") and (article.get("full_text") or article.get("summary")):
                test_article = article
                break

        if not test_article:
            test_article = articles[0]

        title = test_article.get("title", "No title")
        content = test_article.get("full_text") or test_article.get("summary", "")

        print(f"  -> Article: {title[:60]}...")
        print(f"  -> Content length: {len(content)} chars")

        from src.ai_summarizer_gemini import summarize_article

        start_time = datetime.now()
        result = summarize_article(client, title, content[:3000])
        elapsed = (datetime.now() - start_time).total_seconds()

        if result and result.get("summary"):
            print(f"  -> Summary: {result['summary'][:100]}...")
            print(f"  -> Completed in {elapsed:.2f}s")
            print("  -> [PASS] Real article summarization working")
            return True
        else:
            print(f"  -> [WARN] Empty result")
            return False

    except Exception as e:
        print(f"  -> [FAIL] Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="AI Summarizer (Gemini) Test")
    parser.add_argument("--quick", action="store_true", help="API connection check only")
    parser.add_argument("--file", "-f", help="Test with a real news JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("AI Summarizer (Gemini) Test")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Step 1: API connection
    client = test_api_connection()
    if not client:
        print("\n[RESULT] FAIL - Cannot connect to Gemini API")
        return

    # Step 2: Simple request (token check)
    token_ok = test_simple_request(client)
    if not token_ok:
        print("\n[RESULT] FAIL - Token quota issue or API error")
        return

    if args.quick:
        print("\n[RESULT] PASS - API connection and tokens OK")
        return

    # Step 3: Sample summarization
    test_summarize_sample(client)

    # Step 4: Real file test
    if args.file:
        test_with_file(client, args.file)

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
