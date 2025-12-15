# 제약 뉴스 에이전트 - 전체 파이프라인 실행
# 이 스크립트는 뉴스 수집, 본문 스크래핑, AI 요약을 순차적으로 실행합니다.

import subprocess
import sys
from datetime import datetime

def run_step(step_name: str, command: list) -> bool:
    """단일 단계 실행"""
    print(f"\n{'='*60}")
    print(f"📌 {step_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            check=True,
            encoding='utf-8',
            errors='replace'
        )
        print(f"✅ {step_name} 완료!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {step_name} 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           제약 뉴스 에이전트 - 전체 파이프라인               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    today = datetime.now().strftime('%Y%m%d')
    print(f"📅 실행 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📁 생성될 파일들:")
    print(f"   • pharma_news_{today}.json (뉴스 목록)")
    print(f"   • pharma_news_content_{today}.json (본문 포함)")
    print(f"   • pharma_news_summarized_{today}.json (AI 요약 포함)")
    
    # Step 1: 뉴스 스크래핑
    step1_ok = run_step(
        "Step 1: Google 뉴스 스크래핑",
        [sys.executable, "pharma_news_scraper.py"]
    )
    
    if not step1_ok:
        print("\n⚠️ 뉴스 스크래핑 실패. 기존 파일이 있으면 계속 진행합니다.")
    
    # Step 2: 본문 스크래핑
    step2_ok = run_step(
        "Step 2: 기사 본문 스크래핑",
        [sys.executable, "content_scraper.py", "-i", f"pharma_news_{today}.json"]
    )
    
    if not step2_ok:
        print("\n❌ 본문 스크래핑 실패. 파이프라인을 중단합니다.")
        return
    
    # Step 3: AI 요약
    step3_ok = run_step(
        "Step 3: AI 뉴스 요약",
        [sys.executable, "ai_summarizer.py", "-i", f"pharma_news_content_{today}.json"]
    )
    
    if not step3_ok:
        print("\n❌ AI 요약 실패. 결과를 확인하세요.")
        return
    
    # 완료 메시지
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🎉 파이프라인 완료!                       ║
╚══════════════════════════════════════════════════════════════╝

📊 결과 파일: pharma_news_summarized_{today}.json

다음 단계:
  • 결과 파일을 열어 요약 내용을 확인하세요
  • 이메일 발송 기능을 연결할 수 있습니다
    """)


if __name__ == "__main__":
    main()
