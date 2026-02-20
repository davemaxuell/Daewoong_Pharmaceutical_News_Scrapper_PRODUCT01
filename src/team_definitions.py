# Team-based news routing definitions
# Synced from C:/Users/user/Downloads/keywords_all.xlsx

TEAM_DEFINITIONS = {
    '루피어QC팀': {
        'description': 'Keywords for categories: 무균/주사제, 약전',
        'keywords': [
            'aseptic',
            'sterile',
            'sterilization',
            'aseptic processing',
            '무균',
            '무균 공정',
            '멸균',
            'monograph',
            'general chapter',
            'general notice',
            '각조',
            '개별 기준',
            '일반 시험법',
            '일반 기준',
            '총칙',
            '일반 총칙',
        ],
        'categories': [
            '무균/주사제',
            '약전',
        ],
    },
    '루피어생산팀': {
        'description': 'Keywords for categories: 무균/주사제',
        'keywords': [
            'aseptic',
            'sterile',
            'sterilization',
            'aseptic processing',
            '무균',
            '무균 공정',
            '멸균',
        ],
        'categories': [
            '무균/주사제',
        ],
    },
    '오송 QA팀': {
        'description': 'Keywords for categories: 개정/변경, 무균/주사제, 품질 시스템(QMS), Data integrity, 약전, 교차 오염',
        'keywords': [
            'revision',
            'revised',
            '개정',
            'aseptic',
            'sterile',
            'sterilization',
            'aseptic processing',
            '무균',
            '무균 공정',
            '멸균',
            'deviation',
            'investigation',
            'root cause',
            'CAPA',
            'effectiveness check',
            '일탈',
            '조사',
            '근본 원인',
            '유효성 평가',
            '시정 조치',
            '예방 조치',
            'Data integrity',
            'ALCOA',
            'ALCOA+',
            'audit trail',
            'electronic records',
            'Raw data',
            '데이터 완전성',
            '점검 기록',
            '전자 기록',
            '원 기록',
            '원천 기록',
            'monograph',
            'general chapter',
            'general notice',
            '각조',
            '개별 기준',
            '일반 시험법',
            '일반 기준',
            '총칙',
            '일반 총칙',
            'cross contamination',
            'carryover',
            '교차 오염',
            '잔류 오염',
        ],
        'categories': [
            '개정/변경',
            '무균/주사제',
            '품질 시스템(QMS)',
            'Data integrity',
            '약전',
            '교차 오염',
        ],
    },
    '오송QC1팀': {
        'description': 'Keywords for categories: 약전',
        'keywords': [
            'monograph',
            'general chapter',
            'general notice',
            '각조',
            '개별 기준',
            '일반 시험법',
            '일반 기준',
            '총칙',
            '일반 총칙',
        ],
        'categories': [
            '약전',
        ],
    },
    '오송QC2팀': {
        'description': 'Keywords for categories: 약전',
        'keywords': [
            'monograph',
            'general chapter',
            'general notice',
            '각조',
            '개별 기준',
            '일반 시험법',
            '일반 기준',
            '총칙',
            '일반 총칙',
        ],
        'categories': [
            '약전',
        ],
    },
    '오송고형제생산1팀': {
        'description': 'Keywords for categories: 고형제 - 칭량, 고형제 - 과립 & 건조, 고형제 - 타정, 고형제 - 코팅, 교차 오염',
        'keywords': [
            'dispensing',
            'weighing',
            'material handling',
            '칭량',
            'wet granulation',
            'dry granulation',
            'roller compaction',
            '과립',
            '습식 과립',
            '건식 과립',
            'compression',
            'tablet press',
            'turret',
            'punch',
            'die',
            '타정',
            '타정기',
            '터렛',
            '펀치',
            '다이',
            'film coating',
            'enteric coating',
            'functional coating',
            '필름 코팅',
            '장용 코팅',
            '기능성 코팅',
            'cross contamination',
            'carryover',
            '교차 오염',
            '잔류 오염',
        ],
        'categories': [
            '고형제 - 칭량',
            '고형제 - 과립 & 건조',
            '고형제 - 타정',
            '고형제 - 코팅',
            '교차 오염',
        ],
    },
    '오송고형제생산2팀': {
        'description': 'Keywords for categories: 고형제 - 칭량, 고형제 - 과립 & 건조, 고형제 - 타정, 고형제 - 코팅, 교차 오염',
        'keywords': [
            'dispensing',
            'weighing',
            'material handling',
            '칭량',
            'wet granulation',
            'dry granulation',
            'roller compaction',
            '과립',
            '습식 과립',
            '건식 과립',
            'compression',
            'tablet press',
            'turret',
            'punch',
            'die',
            '타정',
            '타정기',
            '터렛',
            '펀치',
            '다이',
            'film coating',
            'enteric coating',
            'functional coating',
            '필름 코팅',
            '장용 코팅',
            '기능성 코팅',
            'cross contamination',
            'carryover',
            '교차 오염',
            '잔류 오염',
        ],
        'categories': [
            '고형제 - 칭량',
            '고형제 - 과립 & 건조',
            '고형제 - 타정',
            '고형제 - 코팅',
            '교차 오염',
        ],
    },
    '오송제제기술팀': {
        'description': 'Keywords for categories: Validation, 교차 오염',
        'keywords': [
            'qualification',
            'DQ',
            'IQ',
            'OQ',
            'PQ',
            'Process validation',
            'continued process verification',
            'Shipping validation',
            '적격성 평가',
            '검증',
            '검정',
            '밸리데이션',
            '공정 밸리데이션',
            '지속적 공정 검증',
            '운송 밸리데이션',
            'cross contamination',
            'carryover',
            '교차 오염',
            '잔류 오염',
        ],
        'categories': [
            'Validation',
            '교차 오염',
        ],
    },
}


def get_team_list() -> list:
    """Return team list."""
    return list(TEAM_DEFINITIONS.keys())


def get_team_prompt() -> str:
    """Build team descriptions for LLM prompt."""
    lines = []
    for team, info in TEAM_DEFINITIONS.items():
        lines.append(f"- {team}: {info['description']}")
    return "\n".join(lines)


def get_all_team_keywords() -> dict:
    """Return all team keywords."""
    return {team: info["keywords"] for team, info in TEAM_DEFINITIONS.items()}


def get_team_categories() -> dict:
    """Return all team categories."""
    return {team: info.get("categories", []) for team, info in TEAM_DEFINITIONS.items()}


def get_teams_by_category(category: str) -> list:
    """Return teams responsible for the given category."""
    teams = []
    for team, info in TEAM_DEFINITIONS.items():
        if category in info.get("categories", []):
            teams.append(team)
    return teams
