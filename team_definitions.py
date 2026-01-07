# 팀별 뉴스 라우팅 정의
# 각 팀의 관심 분야를 정의하여 LLM이 적절한 팀을 선택할 수 있도록 합니다.

TEAM_DEFINITIONS = {
    "해외사업팀": {
        "description": "해외 시장 진출, 수출, 글로벌 파트너십, 현지 법인 설립",
        "keywords": ["해외 진출", "수출", "글로벌", "FDA", "EMA", "미국 시장", "유럽 시장", "중국 시장", "일본 시장", "현지 법인", "해외 파트너"]
    },
    "영업팀": {
        "description": "국내 영업, 매출 실적, 병원/약국 거래, 영업 전략",
        "keywords": ["국내 매출", "영업 실적", "병원 계약", "약국", "도매상", "유통", "처방 실적"]
    },
    "R&D팀": {
        "description": "신약 개발, 임상시험, 연구 성과, 파이프라인, 특허",
        "keywords": ["신약 개발", "임상시험", "임상 1상", "임상 2상", "임상 3상", "파이프라인", "연구", "특허", "기술이전", "라이선스"]
    },
    "마케팅팀": {
        "description": "제품 출시, 브랜드 마케팅, 광고, 프로모션, 시장 점유율",
        "keywords": ["신제품 출시", "브랜드", "마케팅", "광고", "프로모션", "시장 점유율", "소비자"]
    },
    "경영지원팀": {
        "description": "경영 전략, 인사, 재무, 투자, M&A, 주가, 실적 발표",
        "keywords": ["경영", "인사", "재무", "투자", "M&A", "인수합병", "주가", "실적", "매출", "영업이익", "IPO"]
    },
    "RA팀": {
        "description": "규제, 인허가, 식약처, 정책, GMP, 품목허가",
        "keywords": ["식약처", "규제", "인허가", "품목허가", "GMP", "정책", "약가", "보험급여"]
    }
}


def get_team_list() -> list:
    """팀 목록 반환"""
    return list(TEAM_DEFINITIONS.keys())


def get_team_prompt() -> str:
    """LLM 프롬프트용 팀 설명 생성"""
    lines = []
    for team, info in TEAM_DEFINITIONS.items():
        lines.append(f"- {team}: {info['description']}")
    return "\n".join(lines)


def get_all_team_keywords() -> dict:
    """모든 팀의 키워드 반환 (키워드 기반 매칭용)"""
    return {team: info["keywords"] for team, info in TEAM_DEFINITIONS.items()}
