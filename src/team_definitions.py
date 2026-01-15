# 팀별 뉴스 라우팅 정의
# 각 팀의 관심 분야를 정의하여 LLM이 적절한 팀을 선택할 수 있도록 합니다.

TEAM_DEFINITIONS = {
    # ===== 기존 사업 관련 팀 =====
    "해외사업팀": {
        "description": "해외 시장 진출, 수출, 글로벌 파트너십, 현지 법인 설립",
        "keywords": ["해외 진출", "수출", "글로벌", "FDA", "EMA", "미국 시장", "유럽 시장", "중국 시장", "일본 시장", "현지 법인", "해외 파트너"],
        "categories": ["시장/투자"]
    },
    "영업팀": {
        "description": "국내 영업, 매출 실적, 병원/약국 거래, 영업 전략",
        "keywords": ["국내 매출", "영업 실적", "병원 계약", "약국", "도매상", "유통", "처방 실적"],
        "categories": ["제품"]
    },
    "R&D팀": {
        "description": "신약 개발, 임상시험, 연구 성과, 파이프라인, 특허",
        "keywords": ["신약 개발", "임상시험", "임상 1상", "임상 2상", "임상 3상", "파이프라인", "연구", "특허", "기술이전", "라이선스"],
        "categories": ["업계/R&D", "AI"]
    },
    "마케팅팀": {
        "description": "제품 출시, 브랜드 마케팅, 광고, 프로모션, 시장 점유율",
        "keywords": ["신제품 출시", "브랜드", "마케팅", "광고", "프로모션", "시장 점유율", "소비자"],
        "categories": ["제품"]
    },
    "경영지원팀": {
        "description": "경영 전략, 인사, 재무, 투자, M&A, 주가, 실적 발표",
        "keywords": ["경영", "인사", "재무", "투자", "M&A", "인수합병", "주가", "실적", "매출", "영업이익", "IPO"],
        "categories": ["시장/투자", "대웅/관계사", "인력/교육"]
    },
    "RA팀": {
        "description": "규제, 인허가, 식약처, 정책, GMP, 품목허가, 개정 사항",
        "keywords": ["식약처", "규제", "인허가", "품목허가", "GMP", "정책", "약가", "보험급여", "개정", "시행일"],
        "categories": ["정책/행정", "개정/변경"]
    },

    # ===== GMP/QMS 관련 팀 =====
    "QA팀": {
        "description": "품질 시스템(QMS), 일탈/CAPA, 변경관리, 밸리데이션, 데이터 완전성, 위험관리",
        "keywords": [
            "일탈", "CAPA", "변경관리", "변경", "위험 관리", "QRM", "FMEA",
            "밸리데이션", "적격성 평가", "공정 벨리데이션", "DQ", "IQ", "OQ", "PQ",
            "데이터 완전성", "ALCOA", "audit trail", "전자 기록", "CSV",
            "deviation", "change control", "risk assessment", "validation", "data integrity"
        ],
        "categories": ["품질시스템/QMS", "밸리데이션", "데이터 완전성", "개정/변경"]
    },
    "QC팀": {
        "description": "품질관리, 약전 시험법, 시험법 밸리데이션, OOS/OOT, 분석 시험",
        "keywords": [
            "약전", "각조", "일반 시험법", "monograph",
            "시험법 벨리데이션", "시험법 검증", "정확성", "정밀성",
            "용출", "함량", "유연물질", "불순물", "잔류용매",
            "OOS", "OOT", "규격 소외", "안정성",
            "dissolution", "assay", "impurities", "method validation", "stability"
        ],
        "categories": ["약전", "데이터 완전성", "품질시스템/QMS"]
    },
    "무균제조팀": {
        "description": "무균 공정, 주사제 제조, 환경모니터링, APS, CCS, 멸균",
        "keywords": [
            "무균", "멸균", "무균 조작", "aseptic", "sterile",
            "환경모니터링", "EM", "environmental monitoring",
            "청정실", "cleanroom", "HVAC", "HEPA",
            "APS", "media fill", "배지충전시험", "무균공정밸리데이션",
            "엔도톡신", "endotoxin", "pyrogen", "bioburden",
            "CCS", "contamination control strategy", "오염 관리 전략",
            "CCI", "container closure integrity", "용기 완전성 시험"
        ],
        "categories": ["무균/주사제", "교차오염"]
    },
    "고형제제조팀": {
        "description": "고형제 제조(칭량, 과립, 타정, 코팅), 혼합, 교차오염 관리",
        "keywords": [
            "칭량", "혼합", "과립", "타정", "코팅",
            "dispensing", "blending", "granulation", "compression", "coating",
            "습식 과립", "건식 과립", "유동층", "wet granulation", "dry granulation",
            "타정기", "tablet press", "캡핑", "층분리", "capping", "lamination",
            "필름 코팅", "장용 코팅", "film coating", "enteric coating",
            "교차 오염", "cross contamination", "세척 밸리데이션", "cleaning validation",
            "분진 관리", "dust control", "차압", "differential pressure"
        ],
        "categories": ["고형제-칭량/혼합", "고형제-과립/건조", "고형제-타정", "고형제-코팅", "교차오염"]
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


def get_team_categories() -> dict:
    """모든 팀의 카테고리 반환 (카테고리 기반 라우팅용)"""
    return {team: info.get("categories", []) for team, info in TEAM_DEFINITIONS.items()}


def get_teams_by_category(category: str) -> list:
    """특정 카테고리를 담당하는 팀 목록 반환"""
    teams = []
    for team, info in TEAM_DEFINITIONS.items():
        if category in info.get("categories", []):
            teams.append(team)
    return teams
