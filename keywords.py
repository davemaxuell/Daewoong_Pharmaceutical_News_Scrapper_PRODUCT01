# Classification
# Keywords - 제약 산업 관련 키워드

KEYWORDS = {
    "주요전문지 헤드라인": [
        "약가제도 모순",
        "의료개혁 위원회 출범",
        "제조 경쟁력",
        "암 정밀의료",
        "성분명 처방",
        # 추가 키워드
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
        # 추가 키워드
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
        # 추가 키워드
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
        # 추가 키워드
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
        # 추가 키워드
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
        # 추가 키워드
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
        # 새 카테고리
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
        # 새 카테고리
        "제약 채용",
        "제약 연구원",
        "제약 인재 영입",
        "제약 교육",
        "약학대학",
        "제약 인력 양성",
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