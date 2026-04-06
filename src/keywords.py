# Classification
# Keywords synced from C:/Users/user/Downloads/keywords_all.xlsx

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from time import monotonic

KEYWORDS = {
    '개정/변경': [
        'revision',
        'revised',
        '개정',
        '업데이트',
        'update',
        'upated',
        'amendment',
        'amended',
        'corrigendum',
        'errata',
        '정정',
        '수정',
        'draft',
        'consultation',
        'public comment',
        'concept paper',
        '초안',
        'effective date',
        'implementation date',
        'transition period',
        '시행',
        '시행일',
    ],
    '무균/주사제': [
        'aseptic',
        'sterile',
        'sterilization',
        'aseptic processing',
        '무균',
        '무균 공정',
        '멸균',
        'CCS',
        'contamination control strategy',
        '오염 관리 전략',
        'cleanroom',
        'HVAC',
        'HEPA',
        'airflow',
        'smoke study',
        'airflow',
        '청정작업실',
        '청정실',
        '공기 조화 장치',
        '헤파',
        '기류',
        '기류패턴 테스트',
        'environmental monitoring',
        'trending',
        'alert level',
        'action level',
        '환경모니터링',
        '경고수준',
        '조치수준',
        'APS',
        'media fill',
        'worst case',
        'intervention',
        '무균공정모의시험',
        '배지충전시험',
        '메디아필',
        '간섭',
        '최악의 경우',
        'sterilizing filter',
        'integrity test',
        'PUPSIT',
        '멸균 필터',
        '필터 완전성 시험',
        'endotoxin',
        'pyrogen',
        'bioburden',
        '엔도톡신',
        '발열성물질',
        '바이오버든',
        'CCI',
        'container closure integrity',
        'leak test',
        '용기 완전성 시험',
        '용기 마개 완전성 시험',
        'particulates',
        'visible particles',
        'settle plate',
        'contact plate',
        'air sample',
        '부유입자',
        '부유균',
        '낙하균',
        '표면균',
        '미생물',
        '미립자',
    ],
    '품질 시스템(QMS)': [
        'deviation',
        'investigation',
        'root cause',
        'CAPA',
        'effectiveness check',
        '일탈',
        '근본 원인',
        '유효성 평가',
        '시정 조치',
        '예방 조치',
        'changecontrol',
        'change menagement',
        'impact assessment',
        '변경',
        '변경관리',
        '영향평가',
        '영향성 평가',
        'risk assessment',
        'QRM',
        'FMEA',
        '위험 관리',
        '품질 위험 관리',
        '위험 평가',
        'stability',
        'OOS',
        'OOT',
        'data trending',
        '안정성',
        '규격 초과',
        '경향 초과',
    ],
    'Validation': [
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
    ],
    'Data integrity': [
        'Data integrity',
        'ALCOA',
        'ALCOA+',
        'audit trail',
        'electronic records',
        'Raw data',
        '데이터 완전성',
        '점검 기록',
        '전자 기록',
        '원천 기록',
        'Part 11',
        'computerized system validation',
        'CSV',
        '컴퓨터화 시스템',
        '컴퓨터 시스템 밸리데이션',
        'access control',
        'privilege',
        'backup',
        'disaster recovery',
        'security',
        'log review',
        '접근 권한',
        '백업',
        '재난 복구',
    ],
    '약전': [
        'monograph',
        'general chapter',
        'general notice',
        '각조',
        '개별 기준',
        '일반 시험법',
        '일반 기준',
        '총칙',
        '일반 총칙',
        'revision bulletin',
        'official text',
        'harmonization',
        '개정 공지',
        '개정 고시',
        '공식 문서',
        '공식 본문',
        '조화',
        '국제 조화',
        'method validation',
        'verification',
        'specificity',
        'accuracy',
        'precision',
        'robustness',
        '시험법 밸리데이션',
        '시험법 검증',
        '시험법 적합성 확인',
        '검증',
        '특이성',
        '정확성',
        '정밀성',
        '강건성',
        '견고성',
        'impurities',
        'residual solvents',
        'elemental impurities',
        '불순물',
        '순도 시험',
        '잔류용매',
        '잔류용매 시험',
        'dissolution',
        'assay',
        'related substances',
        'sterility test',
        'endotoxin test',
        '용출',
        '용출 시험',
        '정량',
        '함량 시험',
        '함량',
        '유연물질',
        '유연물질 시험',
        '무균 시험',
        '엔도톡신',
    ],
    '고형제 - 칭량': [
        'dispensing',
        'weighing',
        'material handling',
        '칭량',
        'blend',
        'blending',
        'mixing',
        'blend uniformity',
        'content uniformity',
        '혼합',
        '혼합물',
        '혼합 균일성',
        '함량 균일성',
        'segregation',
        'demixing',
        'particle size distribution',
        '성분 분리',
        '탈혼합',
        '입도 분포',
        '입자 크기 분포',
        'flowability',
        'bulk density',
        'tapped density',
        '유동성',
        '겉보기 밀도',
        '다짐 밀도',
    ],
    '고형제 - 과립 & 건조': [
        'wet granulation',
        'dry granulation',
        'roller compaction',
        '과립',
        '습식 과립',
        '건식 과립',
        'fluid bed granulation',
        'high shear granulation',
        '유동층 과립',
        '고전단 과립',
        'drying',
        'LOD',
        'moisture content',
        '건조',
        '건조 감량',
        '수분 함량',
        'over-granulation',
        'under-granulation',
        '과과립',
        '미과립',
        'binder solution',
        'spray rate',
        'inlet air temperature',
        '결합액',
        '분무 속도',
        '유입 공기 온도',
    ],
    '고형제 - 타정': [
        'compression',
        'tablet press',
        'turret',
        'punch',
        '타정',
        '타정기',
        '터렛',
        '펀치',
        'tablet weight variation',
        'hardness',
        'friability',
        '질량 편차',
        '경도',
        '마손도',
        'capping',
        'lamination',
        'sticing',
        'picking',
        '캡핑',
        '층분리',
        '부착',
        '점착',
        '스틱킹',
        '뜯김',
    ],
    '고형제 - 코팅': [
        'film coating',
        'enteric coating',
        'functional coating',
        '필름 코팅',
        '장용 코팅',
        '기능성 코팅',
        'coating uniformity',
        'weight gain',
        '코팅 균일성',
        '중량 증가율',
        'coating defects',
        'orange peel',
        'mottling',
        'cracking',
        'peeling',
        'picking',
        'twinning',
        '코팅 결함',
        '표면 거칠음',
        '얼룩',
        '균열',
        '박리',
        '코팅 뜯김',
        '정제 들러붙음',
        'solvent-based',
        'aqueous coating',
        '유기용매 코팅',
        '수계 코팅',
        'spray gun',
        'atomization',
        'pan speed',
        '스프레이 건',
        '분무 노즐',
        '미립화',
        '분무 미립화',
        '팬 속도',
    ],
    '교차 오염': [
        'cross contamination',
        'carryover',
        '교차 오염',
        '잔류 오염',
        'dust control',
        'dust explosion',
        'ATEX',
        '분진 관리',
        '분진 폭발',
        'cleaning validation',
        'MACO',
        'PED',
        'HBEL',
        '세척 밸리데이션',
        '허용 일일 노출량',
        '최대 허용 이월량',
        'shared equipment',
        'campaign production',
        '공유 설비',
        '캠페인 생산',
        'dedicated equipment',
        '전용 설비',
        '전용 생산 설비',
        'HVAC zoning',
        'pressure cascade',
        'differential pressure',
        '차압',
        '차압 구배',
    ],
}


_RUNTIME_KEYWORDS_CACHE: dict[str, list[str]] | None = None
_RUNTIME_KEYWORDS_LOADED_AT = 0.0
_RUNTIME_KEYWORDS_SOURCE = "static"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPDATED_KEYWORDS_PATH = PROJECT_ROOT / "config" / "updated_keywords.json"
_CONFIG_KEYWORDS_LOADED = False


def _copy_keyword_map(keyword_map: dict[str, list[str]]) -> dict[str, list[str]]:
    return {category: list(keywords) for category, keywords in keyword_map.items()}


def _normalize_keyword(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _load_keywords_from_updated_config() -> dict[str, list[str]] | None:
    if not UPDATED_KEYWORDS_PATH.exists():
        return None

    try:
        payload = json.loads(UPDATED_KEYWORDS_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"[WARN] Failed to load updated keywords config: {exc}")
        return None

    terminology = payload.get("pharmaceutical_terminology", {})
    keyword_map: dict[str, list[str]] = {}

    for raw_item in terminology.values():
        item = raw_item if isinstance(raw_item, dict) else {}
        category_name = str(((item.get("category_name") or {}).get("ko")) or "").strip()
        if not category_name:
            continue

        seen: set[str] = set()
        terms: list[str] = []
        for raw_term_group in item.get("terms", []) or []:
            term_group = raw_term_group if isinstance(raw_term_group, dict) else {}
            for bucket in ("en", "ko"):
                for raw_value in term_group.get(bucket, []) or []:
                    value = str(raw_value or "").strip()
                    if not value:
                        continue
                    normalized = _normalize_keyword(value)
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    terms.append(value)

        if terms:
            keyword_map[category_name] = terms

    return keyword_map or None


_UPDATED_KEYWORDS = _load_keywords_from_updated_config()
if _UPDATED_KEYWORDS:
    KEYWORDS = _UPDATED_KEYWORDS
    _CONFIG_KEYWORDS_LOADED = True


def _get_keyword_cache_ttl_seconds() -> int:
    raw = (os.getenv("SCRAPER_KEYWORD_CACHE_TTL_SECONDS") or "300").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 300


def _get_database_url() -> str:
    try:
        from src.env_config import first_env, load_project_env
    except Exception:
        return ""

    load_project_env()
    return first_env("DATABASE_URL")


def _load_keywords_via_project_venv() -> dict[str, list[str]] | None:
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
    if not venv_python.exists():
        return None

    current_python = Path(sys.executable).absolute()
    if venv_python.absolute() == current_python:
        return None

    helper = """
import json
from psycopg import connect
from src.env_config import first_env, load_project_env

def normalize_keyword(value: str) -> str:
    return " ".join(value.strip().lower().split())

load_project_env()
database_url = first_env("DATABASE_URL")
if not database_url:
    raise SystemExit(2)

keyword_map = {}
seen_by_category = {}

with connect(database_url, connect_timeout=5) as conn:
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT c.name, k.keyword
            FROM keywords AS k
            JOIN keyword_category_map AS km
              ON km.keyword_id = k.id
            JOIN categories AS c
              ON c.id = km.category_id
            WHERE k.is_active IS TRUE
            ORDER BY c.name ASC, k.keyword ASC
            '''
        )
        for category_name, keyword in cur.fetchall():
            category = str(category_name or '').strip()
            keyword_value = str(keyword or '').strip()
            if not category or not keyword_value:
                continue
            normalized = normalize_keyword(keyword_value)
            seen = seen_by_category.setdefault(category, set())
            if normalized in seen:
                continue
            seen.add(normalized)
            keyword_map.setdefault(category, []).append(keyword_value)

print(json.dumps(keyword_map, ensure_ascii=False))
"""

    try:
        result = subprocess.run(
            [str(venv_python), "-c", helper],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=15,
        )
    except Exception:
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    keyword_map: dict[str, list[str]] = {}
    for category_name, keywords in payload.items():
        category = str(category_name or "").strip()
        if not category or not isinstance(keywords, list):
            continue
        cleaned_keywords = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
        if cleaned_keywords:
            keyword_map[category] = cleaned_keywords
    return keyword_map


def _load_keywords_from_admin_db() -> dict[str, list[str]] | None:
    try:
        from psycopg import connect
    except Exception:
        return _load_keywords_via_project_venv()

    database_url = _get_database_url()
    if not database_url:
        return None

    keyword_map: dict[str, list[str]] = {}
    seen_by_category: dict[str, set[str]] = {}

    try:
        with connect(database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.name, k.keyword
                    FROM keywords AS k
                    JOIN keyword_category_map AS km
                      ON km.keyword_id = k.id
                    JOIN categories AS c
                      ON c.id = km.category_id
                    WHERE k.is_active IS TRUE
                    ORDER BY c.name ASC, k.keyword ASC
                    """
                )
                for category_name, keyword in cur.fetchall():
                    category = str(category_name or "").strip()
                    keyword_value = str(keyword or "").strip()
                    if not category or not keyword_value:
                        continue

                    normalized = _normalize_keyword(keyword_value)
                    seen = seen_by_category.setdefault(category, set())
                    if normalized in seen:
                        continue

                    seen.add(normalized)
                    keyword_map.setdefault(category, []).append(keyword_value)
    except Exception as exc:
        print(f"[WARN] Falling back to bundled keywords; failed to load admin DB keywords: {exc}")
        return None

    return keyword_map


def get_runtime_keywords(force_refresh: bool = False) -> dict[str, list[str]]:
    """Return the keyword map currently used by scraper classification."""
    global _RUNTIME_KEYWORDS_CACHE
    global _RUNTIME_KEYWORDS_LOADED_AT
    global _RUNTIME_KEYWORDS_SOURCE

    ttl_seconds = _get_keyword_cache_ttl_seconds()
    if (
        not force_refresh
        and _RUNTIME_KEYWORDS_CACHE is not None
        and ttl_seconds > 0
        and (monotonic() - _RUNTIME_KEYWORDS_LOADED_AT) < ttl_seconds
    ):
        return _copy_keyword_map(_RUNTIME_KEYWORDS_CACHE)

    admin_keywords = _load_keywords_from_admin_db()
    if admin_keywords is None:
        if _get_database_url():
            raise RuntimeError(
                "Failed to load active keywords from the admin database. "
                "Scraper classification is configured to use the admin-managed keywords."
            )
        _RUNTIME_KEYWORDS_CACHE = _copy_keyword_map(KEYWORDS)
        _RUNTIME_KEYWORDS_SOURCE = "updated_keywords_json" if _CONFIG_KEYWORDS_LOADED else "static"
    else:
        _RUNTIME_KEYWORDS_CACHE = _copy_keyword_map(admin_keywords)
        _RUNTIME_KEYWORDS_SOURCE = "admin_db"

    _RUNTIME_KEYWORDS_LOADED_AT = monotonic()
    return _copy_keyword_map(_RUNTIME_KEYWORDS_CACHE)


def get_all_keywords():
    """Return all runtime keywords used by scraper classification."""
    all_kw = []
    for keywords in get_runtime_keywords().values():
        all_kw.extend(keywords)
    return sorted(set(all_kw), key=str.lower)


def get_categories():
    """Return runtime categories used by scraper classification."""
    return list(get_runtime_keywords().keys())


def classify_article(title: str, text: str = "") -> tuple[list, list]:
    """Classify an article using the runtime keyword map."""
    content = (title + " " + text).lower()
    matched_classifications = []
    matched_keywords = []

    for classification, keywords in get_runtime_keywords().items():
        for keyword in keywords:
            if keyword.lower() in content:
                if classification not in matched_classifications:
                    matched_classifications.append(classification)
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

    return matched_classifications, matched_keywords


def get_gmp_categories():
    """Return runtime GMP/QMS categories used by scraper classification."""
    return list(get_runtime_keywords().keys())
