# Classification
# Keywords - 제약 산업 관련 키워드 (GMP/QMS 용어 포함)

KEYWORDS = {
    # ===== 일반 정책/산업 키워드 =====
    "일반 정책/산업": [
        "제조 경쟁력",
        "제조경쟁력",
        "제약 산업",
        "식의약 정책 소통",
        "식약처",
        "GMP",
        "규제 완화",
        "의약품 제조 경쟁력",
    ],

    # ===== GMP/QMS 전문 용어 카테고리 (updated_keywords.json 기반) =====
    "개정/변경": [
        # English terms
        "revision", "revised", "update", "updated", "amendment", "amended",
        "corrigendum", "errata", "draft", "consultation", "public comment",
        "concept paper", "effective date", "implementation date", "transition period",
        # Korean terms
        "개정", "업데이트", "정정", "수정", "초안", "시행", "시행일",
    ],
    "무균/주사제": [
        # English terms
        "aseptic", "sterile", "sterilization", "aseptic processing",
        "CCS", "contamination control strategy",
        "cleanroom", "HVAC", "HEPA", "airflow", "smoke study",
        "EM", "environmental monitoring", "trending", "alert level", "action level",
        "APS", "media fill", "worst case", "intervention",
        "sterilizing filter", "integrity test", "PUPSIT",
        "endotoxin", "pyrogen", "bioburden",
        "CCI", "container closure integrity", "leak test",
        "particulates", "visible particles", "settle plate", "contact plate", "air sample",
        # Korean terms
        "무균", "무균 조작", "멸균", "오염 관리 전략",
        "청정작업실", "청정실", "공기 조화 장치", "헤파", "기류", "기류패턴 테스트",
        "환경모니터링", "경고수준", "조시수준",
        "무균공정밸리데이션", "배지충전시험", "메디어필", "간섭", "최악의 경우",
        "멸균 필터", "필터 완전성 시험",
        "엔도톡신", "발열성물질", "바이오버든",
        "용기 완전성 시험", "용기 마개 완전성 시험",
        "부유입자", "부유분", "낙하균", "표면균", "미생물", "미립자",
    ],
    "품질시스템/QMS": [
        # English terms
        "deviation", "investigation", "root cause", "CAPA", "effectiveness check",
        "change control", "change management", "impact assessment",
        "risk assessment", "QRM", "FMEA",
        "stability", "OOS", "OOT", "data trending",
        # Korean terms
        "일탈", "조사", "근본 원인", "유효성 평가", "시정 조치", "예방 조치",
        "변경", "변경관리", "영향평가", "영향성 평가",
        "위험 관리", "품질 위험 관리", "위험 평가",
        "안정성", "규격 소외", "경향 소외",
    ],
    "밸리데이션": [
        # English terms
        "qualification", "DQ", "IQ", "OQ", "PQ",
        "process validation", "continued process verification", "shipping validation",
        # Korean terms
        "적격성 평가", "검증", "벨리데이션",
        "공정 벨리데이션", "지속적 공정 검증", "운송 벨리데이션",
    ],
    "데이터 완전성": [
        # English terms
        "data integrity", "ALCOA", "ALCOA+", "audit trail", "electronic records", "raw data",
        "Part 11", "computerized system validation", "CSV",
        "access control", "privilege", "backup", "disaster recovery", "security", "log review",
        # Korean terms
        "데이터 완전성", "점검 기록", "전자 기록", "원 기록", "원천 기록",
        "컴퓨터화 시스템", "컴퓨터 시스템 벨리데이션",
        "접근 관리", "백업", "재난 복구",
    ],
    "약전": [
        # English terms
        "monograph", "general chapter", "general notice",
        "revision bulletin", "official text", "harmonization",
        "method validation", "verification", "specificity", "accuracy", "precision", "robustness",
        "impurities", "residual solvents", "elemental impurities",
        "dissolution", "assay", "related substances", "sterility test", "endotoxin test",
        # Korean terms
        "각조", "개별 기준", "각 약전 시험법", "일반 기준", "총칙", "일반 총칙",
        "개정 공지", "개정 고시", "공식 문서", "공식 단독", "조화", "국제 조화",
        "시험법 벨리데이션", "시험법 검증", "시험법 적합성 확인", "특이성", "정확성", "정밀성", "견고성", "건고성",
        "불순물", "순도 시험", "잔류용매", "산류용매 시험",
        "용출", "용출 시험", "함량", "함량 시험", "유연물질", "유연물질 시험", "무균 시험",
    ],
    "고형제-칭량/혼합": [
        # English terms
        "dispensing", "weighing", "material handling",
        "blend", "blending", "mixing", "blend uniformity", "content uniformity",
        "segregation", "demixing", "particle size distribution",
        "flowability", "bulk density", "tapped density",
        # Korean terms
        "칭량", "혼합", "혼합물", "혼합 균일성", "함량 균일성",
        "분리", "성분 분리", "탈혼합", "입도 분포", "입자 크기 분포",
        "유동성", "겉보기 밀도", "다짐 밀도",
    ],
    "고형제-과립/건조": [
        # English terms
        "wet granulation", "dry granulation", "roller compaction",
        "fluid bed granulation", "high shear granulation",
        "drying", "LOD", "moisture content",
        "over-granulation", "under-granulation",
        "binder solution", "spray rate", "inlet air temperature",
        # Korean terms
        "과립", "습식 과립", "건식 과립",
        "유동층 과립", "고전단 과립",
        "건조", "건조 감량", "수분 함량",
        "과과립", "미과립",
        "결합액", "분무 속도", "유입 공기 온도",
    ],
    "고형제-타정": [
        # English terms
        "compression", "tablet press", "turret", "punch", "die",
        "tablet weight variation", "hardness", "friability",
        "capping", "lamination", "sticking", "picking",
        # Korean terms
        "타정", "타정기", "타렛", "펀치", "다이",
        "질량 편차", "경도", "마손도",
        "캡핑", "층분리", "부착", "점착", "스티킹", "픈킹",
    ],
    "고형제-코팅": [
        # English terms
        "film coating", "enteric coating", "functional coating",
        "coating uniformity", "weight gain",
        "coating defects", "orange peel", "mottling", "cracking", "peeling", "twinning",
        "solvent-based", "aqueous coating",
        "spray gun", "atomization", "pan speed",
        # Korean terms
        "필름 코팅", "장용 코팅", "기능성 코팅",
        "코팅 균일성", "중량 증가율",
        "코팅 결함", "표면 거칠음", "얼룩", "균열", "박리", "코팅 뜯김", "정제 들러붙음",
        "유기용매 코팅", "수계 코팅",
        "스프레이 건", "분무 노즐", "미립화", "분무 미립화", "팬 속도",
    ],
    "교차오염": [
        # English terms
        "cross contamination", "carryover",
        "dust control", "dust explosion", "ATEX",
        "cleaning validation", "MACO", "PED", "HBEL",
        "shared equipment", "campaign production",
        "dedicated equipment",
        "HVAC zoning", "pressure cascade", "differential pressure",
        # Korean terms
        "교차 오염", "잔류 오염",
        "분진 관리", "분진 폭발",
        "세척 밸리데이션", "허용 일일 노출량", "최대 허용 이월량",
        "공유 설비", "캠페인 생산",
        "전용 설비", "전용 생산 설비",
        "차압", "차압 구배",
    ],
}


def get_all_keywords():
    """모든 키워드 리스트 반환"""
    all_kw = []
    for category, keywords in KEYWORDS.items():
        all_kw.extend(keywords)
    return list(set(all_kw))  # 중복 제거


def get_categories():
    """카테고리 목록 반환"""
    return list(KEYWORDS.keys())


def classify_article(title: str, text: str = "") -> tuple[list, list]:
    """
    기사 제목과 본문에서 키워드 매칭하여 분류 및 키워드 반환
    Returns: (classifications, matched_keywords)
    """
    content = (title + " " + text).lower()
    matched_classifications = []
    matched_keywords = []
    
    for classification, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in content:
                if classification not in matched_classifications:
                    matched_classifications.append(classification)
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
    
    return matched_classifications, matched_keywords


def get_gmp_categories():
    """GMP/QMS 관련 카테고리만 반환"""
    gmp_cats = [
        "개정/변경", "무균/주사제", "품질시스템/QMS", "밸리데이션",
        "데이터 완전성", "약전", "고형제-칭량/혼합", "고형제-과립/건조",
        "고형제-타정", "고형제-코팅", "교차오염"
    ]
    return [cat for cat in gmp_cats if cat in KEYWORDS]