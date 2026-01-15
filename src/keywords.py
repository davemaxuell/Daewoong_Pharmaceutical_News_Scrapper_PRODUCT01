# Classification
# Keywords - 제약 산업 관련 키워드 (GMP/QMS 용어 포함)

KEYWORDS = {
    # ===== 기존 뉴스 분류 카테고리 =====
    "주요전문지 헤드라인": [
        "약가제도 모순",
        "의료개혁 위원회 출범",
        "제조 경쟁력",
        "암 정밀의료",
        "성분명 처방",
        "제약 산업",
        "헬스케어",
        "의료 정책",
        "건강보험",
        "약사회",
        "의사협회",
        "병원 경영",
    ],
    "대웅/관계사": [
        "디지털헬스케어",
        "시지바이오",
        "한올바이오",
        "국가핵심기술",
        "대웅제약",
        "바이오벤처",
        "CMO",
        "CDMO",
        "위탁생산",
    ],
    "정책/행정": [
        "식의약 정책 소통",
        "희귀의약품 기준 완화",
        "약가 인하",
        "가짜 앰뷸런스",
        "복지부 인사",
        "성분명 처방",
        "마스크 주의사항",
        "식약처",
        "FDA 승인",
        "품목허가",
        "임상시험 승인",
        "GMP",
        "규제 완화",
        "의약품 허가",
        "약가 협상",
        "건강보험심사평가원",
        "보건복지부",
    ],
    "AI": [
        "의약품 제조 경쟁력",
        "AI 신약 개발",
        "인공지능 신약",
        "AI 진단",
        "딥러닝 의료",
        "머신러닝 제약",
        "AI 임상",
        "빅데이터 헬스케어",
        "디지털 치료제",
        "DTx",
        "AI 기반",
        "데이터 분석",
    ],
    "업계/R&D": [
        "비만치료제 신속심사",
        "FDA 임상시험 완화",
        "항암 신약 패스트트랙",
        "영유아 독감 백신 허가",
        "인공 신경 이식재 승인",
        "신약 개발",
        "바이오시밀러",
        "바이오의약품",
        "항체 치료제",
        "면역항암제",
        "CAR-T",
        "세포치료제",
        "유전자치료",
        "mRNA",
        "임상 1상",
        "임상 2상",
        "임상 3상",
        "파이프라인",
        "기술이전",
        "라이선스 아웃",
        "오픈이노베이션",
        "R&D 투자",
        "신약 후보물질",
        "GLP-1",
        "비만 치료",
        "당뇨병 치료",
        "알츠하이머",
        "치매 치료",
        "희귀질환",
    ],
    "제품": [
        "구강청결 스프레이",
        "건조성 피부질환 개선",
        "단백질 보충제",
        "신제품 출시",
        "의약품 리콜",
        "부작용 보고",
        "약효",
        "복용법",
        "처방전",
        "일반의약품",
        "전문의약품",
        "건강기능식품",
        "비타민",
        "영양제",
    ],
    "시장/투자": [
        "제약 주가",
        "바이오 주가",
        "IPO",
        "제약 상장",
        "바이오 상장",
        "바이오 투자 유치",
        "시리즈 펀딩",
        "M&A",
        "인수합병",
        "바이오 글로벌 진출",
        "제약 수출",
        "해외 제약 시장",
        "미국 제약 시장",
        "중국 제약 시장",
        "유럽 제약 시장",
    ],
    "인력/교육": [
        "제약 채용",
        "제약 연구원",
        "제약 인재 영입",
        "제약 교육",
        "약학대학",
        "제약 인력 양성",
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