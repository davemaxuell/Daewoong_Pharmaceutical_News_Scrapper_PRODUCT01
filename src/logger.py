# 로깅 모듈 - 스크래퍼 실행 기록 관리
# 매일 실행 결과를 로그 파일에 저장하고 추적합니다.

import os
import json
from datetime import datetime
from typing import Optional

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "scraper_history.json")


def ensure_log_dir():
    """로그 디렉토리 생성"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def load_history() -> list:
    """실행 기록 로드"""
    ensure_log_dir()
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_history(history: list):
    """실행 기록 저장"""
    ensure_log_dir()
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def log_execution(
    total_articles: int,
    source_stats: dict,
    classification_stats: dict,
    output_file: str,
    error: Optional[str] = None
):
    """
    실행 결과 기록
    
    Args:
        total_articles: 수집된 총 기사 수
        source_stats: 소스별 통계 {source_name: count}
        classification_stats: 분류별 통계 {classification: count}
        output_file: 저장된 JSON 파일명
        error: 오류 메시지 (있을 경우)
    """
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "total_articles": total_articles,
        "source_stats": source_stats,
        "classification_stats": classification_stats,
        "output_file": output_file,
        "success": error is None,
        "error": error
    }
    
    history.append(entry)
    
    # 최근 90일치만 보관
    if len(history) > 90:
        history = history[-90:]
    
    save_history(history)
    
    # 일별 상세 로그도 저장
    daily_log_file = os.path.join(LOG_DIR, f"log_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(daily_log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"실행 시간: {entry['timestamp']}\n")
        f.write(f"총 기사 수: {total_articles}\n")
        f.write(f"출력 파일: {output_file}\n")
        
        if source_stats:
            f.write("\n[소스별 통계]\n")
            for src, count in sorted(source_stats.items(), key=lambda x: -x[1]):
                f.write(f"  - {src}: {count}개\n")
        
        if classification_stats:
            f.write("\n[분류별 통계]\n")
            for cls, count in sorted(classification_stats.items(), key=lambda x: -x[1]):
                f.write(f"  - {cls}: {count}개\n")
        
        if error:
            f.write(f"\n[오류] {error}\n")
        
        f.write(f"{'='*60}\n")
    
    return entry


def get_recent_executions(days: int = 7) -> list:
    """최근 N일간 실행 기록 조회"""
    history = load_history()
    
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    return [h for h in history if h.get("timestamp", "") >= cutoff]


def print_summary():
    """실행 기록 요약 출력"""
    recent = get_recent_executions(7)
    
    if not recent:
        print("[INFO] 최근 7일간 실행 기록이 없습니다.")
        return
    
    print("\n" + "=" * 60)
    print("📊 최근 7일간 스크래퍼 실행 기록")
    print("=" * 60)
    
    total_articles = sum(r.get("total_articles", 0) for r in recent)
    success_count = sum(1 for r in recent if r.get("success", False))
    
    print(f"\n실행 횟수: {len(recent)}회 (성공: {success_count}회)")
    print(f"총 수집 기사: {total_articles}개")
    
    print("\n[일별 기록]")
    for r in recent[-7:]:
        status = "✅" if r.get("success") else "❌"
        print(f"  {r.get('date', 'N/A')} {r.get('time', '')}: {status} {r.get('total_articles', 0)}개")
    
    print("=" * 60)


if __name__ == "__main__":
    print_summary()
