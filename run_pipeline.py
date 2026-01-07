# 제약 뉴스 에이전트 - 통합 파이프라인
# 1. 뉴스 스크래핑 및 요약 (Gemini)
# 2. 규제 모니터링 및 PDF 분석 (Gemini)
# 3. 이메일 발송

import subprocess
import sys
import os
from datetime import datetime

import json

def run_step(step_name: str, command: list) -> bool:
    """단일 단계 실행"""
    print(f"\n{'='*60}")
    print(f"[STEP] {step_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            check=True,
            encoding='utf-8',
            errors='replace'
        )
        print(f"[SUCCESS] {step_name} completed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAILED] {step_name}: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    print("""
================================================================
       Pharmaceutical News Agent - Full Pipeline (v2.0)
================================================================
    """)
    
    today = datetime.now().strftime('%Y%m%d')
    is_monday = datetime.now().weekday() == 0
    days_back = 3 if is_monday else 1
    
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Day: {'Monday' if is_monday else 'Weekday'}")
    print(f"Days back: {days_back}")
    
    python_exe = sys.executable
    
    # Files
    news_file = f"multi_source_news_{today}.json"
    summarized_file = f"multi_source_summarized_{today}.json"
    monitor_file = f"monitor_updates_{today}.json"
    
    # ---------------------------------------------------------
    # PART 1: NEWS PIPELINE (Scrapers now fetch full content!)
    # ---------------------------------------------------------
    print("\n[PHASE 1] News Scraping & Summarization")
    
    # 1. Scrape News (with full content)
    if not run_step("Multi-Source Scraper", [python_exe, "multi_source_scraper.py", "--days", str(days_back), "-o", news_file]):
        print("[WARNING] Scraping failed. Continuing potentially with partial data...")

    # 2. AI Summarization (Gemini) - directly on news file (now has full_text)
    if os.path.exists(news_file):
        run_step("AI Summarizer (Gemini)", [python_exe, "ai_summarizer_gemini.py", "-i", news_file, "-o", summarized_file])
    else:
        print(f"[ERROR] News file {news_file} not found. Skipping AI summarization.")

    # ---------------------------------------------------------
    # PART 2: MONITOR PIPELINE
    # ---------------------------------------------------------
    print("\n[PHASE 2] Regulatory Monitoring")
    
    # 1. HTML Change Monitor (Static Pages)
    # run_step("HTML Change Monitor", [python_exe, "html_change_monitor.py"])
    
    # 2. ICH & PDF Monitor Pipeline
    run_step("ICH & PDF Monitor", [python_exe, "monitor_pipeline.py"])

    # ---------------------------------------------------------
    # PART 3: REPORTING
    # ---------------------------------------------------------
    print("\n[PHASE 3] Reporting")
    
    # Email Sender
    # 1. Send News Briefing (Always)
    if os.path.exists(summarized_file):
        run_step("Email Distributor (News)", [python_exe, "email_sender.py", "-i", summarized_file])
    
    # 2. Send Monitor Updates (Only if changes detected)
    if os.path.exists(monitor_file):
        try:
            with open(monitor_file, 'r', encoding='utf-8') as f:
                updates = json.load(f)
            
            if updates and len(updates) > 0:
                print(f"\n[INFO] {len(updates)} regulatory updates found. Sending alerts...")
                run_step("Email Distributor (Monitor)", [
                    python_exe, "email_sender.py", 
                    "-i", monitor_file, 
                    "--monitor"
                ])
            else:
                print("\n[INFO] No regulatory updates to report. Email skipped.")
                
        except Exception as e:
            print(f"[ERROR] Failed to check monitor file: {e}")
        
    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
