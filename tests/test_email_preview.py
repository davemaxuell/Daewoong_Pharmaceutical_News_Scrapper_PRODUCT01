#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Preview email HTML in browser (no actual sending)
Usage: python tests/test_email_preview.py --news
       python tests/test_email_preview.py --monitor
"""

import sys
import os
import argparse
import webbrowser
import tempfile
from datetime import datetime

# Setup project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.email_sender import create_email_html, create_monitor_email_html


# Sample data for preview
SAMPLE_ARTICLES = [
    {
        "title": "FDA, 신약 승인 절차 간소화 방안 발표",
        "source": "약업신문",
        "published": "2026-01-15",
        "link": "https://example.com/article1",
        "ai_analysis": {
            "ai_summary": "미국 FDA가 신약 승인 절차를 간소화하는 새로운 가이드라인을 발표했습니다. 이번 변경으로 임상시험 기간이 단축될 것으로 예상됩니다.",
            "key_points": [
                "임상 2상 결과 기반 조건부 승인 확대",
                "실사용 데이터(RWD) 활용 강화",
                "희귀질환 치료제 심사 기간 단축"
            ],
            "industry_impact": "글로벌 제약사들의 신약 개발 전략에 영향을 미칠 것으로 예상됨",
            "ai_keywords": ["FDA", "신약 승인", "임상시험", "희귀질환"]
        }
    },
    {
        "title": "EMA, GMP Annex 1 개정안 시행 일정 공개",
        "source": "GMP Journal",
        "published": "2026-01-14",
        "link": "https://example.com/article2",
        "ai_analysis": {
            "ai_summary": "유럽의약품청(EMA)이 무균 의약품 제조를 위한 GMP Annex 1 개정안의 상세 시행 일정을 발표했습니다.",
            "key_points": [
                "2026년 8월부터 단계적 시행",
                "오염관리전략(CCS) 문서화 필수",
                "환경모니터링 주기 강화"
            ],
            "industry_impact": "무균 제제 생산 업체들의 시설 투자 증가 예상",
            "ai_keywords": ["GMP", "Annex 1", "무균", "EMA"]
        }
    },
    {
        "title": "일본 PMDA, 바이오시밀러 가이드라인 업데이트",
        "source": "PMDA Newsletter",
        "published": "2026-01-13",
        "link": "https://example.com/article3",
        "ai_analysis": {
            "ai_summary": "PMDA가 바이오시밀러 의약품의 품질 평가 기준을 강화하는 새로운 가이드라인을 발표했습니다.",
            "key_points": [
                "동등성 시험 기준 명확화",
                "면역원성 평가 요구사항 추가",
                "외삽 적용 범위 확대"
            ],
            "industry_impact": "바이오시밀러 개발사들의 임상 전략 수정 필요",
            "ai_keywords": ["PMDA", "바이오시밀러", "가이드라인"]
        }
    }
]

SAMPLE_UPDATES = [
    {
        "source": "ICH Guidelines",
        "category": "Q12",
        "link": "https://example.com/ich-q12.pdf",
        "timestamp": "2026-01-15T10:00:00",
        "ai_analysis": {
            "summary": "ICH Q12 기술 및 규제 고려사항에 대한 개정안이 발표되었습니다. 제품 수명 주기 관리에 대한 새로운 접근 방식을 제시합니다.",
            "key_changes": [
                "확립된 조건(EC) 개념 도입",
                "허가 후 변경 관리 체계 간소화",
                "규제 유연성 확대"
            ],
            "implications": "의약품 제조업체들은 제품 라이프사이클 관리 전략을 재검토해야 합니다."
        }
    },
    {
        "source": "USP Pending Monographs",
        "category": "Aspirin Tablets",
        "link": "https://example.com/usp-aspirin.pdf",
        "timestamp": "2026-01-14T15:30:00",
        "ai_analysis": {
            "summary": "아스피린 정제 모노그래프 개정안이 공개 의견 수렴 중입니다.",
            "key_changes": [
                "용출 시험법 변경",
                "유연물질 규격 강화",
                "표준품 요구사항 업데이트"
            ],
            "implications": "아스피린 제제 생산업체는 시험법 밸리데이션 계획 수립 필요"
        }
    }
]


def preview_news_email(team_name: str = "R&D팀"):
    """Preview news briefing email"""
    print(f"\n[INFO] Generating news email preview for {team_name}...")
    
    html = create_email_html(team_name, SAMPLE_ARTICLES)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        temp_path = f.name
    
    print(f"[INFO] Opening in browser: {temp_path}")
    webbrowser.open(f"file://{temp_path}")
    
    print("[SUCCESS] Email preview opened in browser")
    return temp_path


def preview_monitor_email(team_name: str = "RA팀"):
    """Preview monitor alert email"""
    print(f"\n[INFO] Generating monitor email preview for {team_name}...")
    
    html = create_monitor_email_html(team_name, SAMPLE_UPDATES)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        temp_path = f.name
    
    print(f"[INFO] Opening in browser: {temp_path}")
    webbrowser.open(f"file://{temp_path}")
    
    print("[SUCCESS] Email preview opened in browser")
    return temp_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview email templates")
    parser.add_argument("--news", action="store_true", help="Preview news email")
    parser.add_argument("--monitor", action="store_true", help="Preview monitor email")
    parser.add_argument("--team", "-t", default="R&D팀", help="Team name for preview")
    parser.add_argument("--all", "-a", action="store_true", help="Preview all email types")
    
    args = parser.parse_args()
    
    if args.all:
        preview_news_email(args.team)
        preview_monitor_email("RA팀")
    elif args.news:
        preview_news_email(args.team)
    elif args.monitor:
        preview_monitor_email(args.team)
    else:
        print("Usage:")
        print("  python tests/test_email_preview.py --news")
        print("  python tests/test_email_preview.py --monitor")
        print("  python tests/test_email_preview.py --all")
        print("\nOptions:")
        print("  --team, -t : Specify team name (default: R&D팀)")
