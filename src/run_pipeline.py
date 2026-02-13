# 제약 뉴스 에이전트 - 통합 파이프라인
# 1. 뉴스 스크래핑 및 요약 (Gemini)
# 2. 규제 모니터링 및 PDF 분석 (Gemini)
# 3. 이메일 발송

import subprocess
import sys
import os
from datetime import datetime, timedelta
import glob
import json

# Get the project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_NEWS_DIR = os.path.join(PROJECT_ROOT, "data", "news")
DATA_MONITORS_DIR = os.path.join(PROJECT_ROOT, "data", "monitors")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

# Ensure data directories exist
os.makedirs(DATA_NEWS_DIR, exist_ok=True)
os.makedirs(DATA_MONITORS_DIR, exist_ok=True)

# Load .env from config directory
from dotenv import load_dotenv
load_dotenv(os.path.join(CONFIG_DIR, ".env"))


def cleanup_old_files(days_old: int = 14):
    """
    Delete old scraped news files and logs older than specified days.
    Helps manage disk space on the server.
    """
    print(f"\n[CLEANUP] Removing files older than {days_old} days...")
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    deleted_count = 0
    
    # Patterns to clean up
    patterns = [
        os.path.join(DATA_NEWS_DIR, "multi_source_news_*.json"),
        os.path.join(DATA_NEWS_DIR, "multi_source_summarized_*.json"),
        os.path.join(DATA_MONITORS_DIR, "monitor_updates_*.json"),
        os.path.join(PROJECT_ROOT, "logs", "cron_*.log"),
    ]
    
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                # Extract date from filename (YYYYMMDD format)
                filename = os.path.basename(filepath)
                # Find 8-digit date pattern
                import re
                date_match = re.search(r'(\d{8})', filename)
                
                if date_match:
                    file_date_str = date_match.group(1)
                    file_date = datetime.strptime(file_date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        os.remove(filepath)
                        print(f"  [DELETED] {filepath}")
                        deleted_count += 1
            except Exception as e:
                # Skip files that can't be parsed or deleted
                continue
    
    if deleted_count > 0:
        print(f"[CLEANUP] Deleted {deleted_count} old files.")
    else:
        print(f"[CLEANUP] No old files to delete.")

def run_step(step_name: str, command: list, cwd: str = None) -> bool:
    """단일 단계 실행"""
    print(f"\n{'='*60}")
    print(f"[STEP] {step_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            check=True,
            encoding='utf-8',
            errors='replace',
            cwd=cwd or SRC_DIR
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
    print(f"Project root: {PROJECT_ROOT}")
    
    # Cleanup old files (older than 14 days)
    cleanup_old_files(days_old=14)
    
    python_exe = sys.executable
    
    # Files (now in data directories)
    news_file = os.path.join(DATA_NEWS_DIR, f"multi_source_news_{today}.json")
    summarized_file = os.path.join(DATA_NEWS_DIR, f"multi_source_summarized_{today}.json")
    monitor_file = os.path.join(DATA_MONITORS_DIR, f"monitor_updates_{today}.json")
    team_emails_file = os.path.join(CONFIG_DIR, "team_emails.json")
    
    # ---------------------------------------------------------
    # PART 1: NEWS PIPELINE (Scrapers now fetch full content!)
    # ---------------------------------------------------------
    print("\n[PHASE 1] News Scraping & Summarization")
    
    # 1. Scrape News (with full content)
    scraper_script = os.path.join(SRC_DIR, "multi_source_scraper.py")
    if not run_step("Multi-Source Scraper", [python_exe, scraper_script, "--days", str(days_back), "-o", news_file], cwd=PROJECT_ROOT):
        print("[WARNING] Scraping failed. Continuing potentially with partial data...")

    # 2. AI Summarization (Gemini) - directly on news file (now has full_text)
    summarizer_script = os.path.join(SRC_DIR, "ai_summarizer_gemini.py")
    if os.path.exists(news_file):
        run_step("AI Summarizer (Gemini)", [python_exe, summarizer_script, "-i", news_file, "-o", summarized_file], cwd=PROJECT_ROOT)
    else:
        print(f"[ERROR] News file {news_file} not found. Skipping AI summarization.")

    # ---------------------------------------------------------
    # PART 2: MONITOR PIPELINE
    # ---------------------------------------------------------
    print("\n[PHASE 2] Regulatory Monitoring")
    
    # ICH & PDF Monitor Pipeline
    monitor_script = os.path.join(SRC_DIR, "monitor_pipeline.py")
    run_step("ICH & PDF Monitor", [python_exe, monitor_script], cwd=PROJECT_ROOT)

    # ---------------------------------------------------------
    # PART 3: REPORTING
    # ---------------------------------------------------------
    print("\n[PHASE 3] Reporting")
    
    email_script = os.path.join(SRC_DIR, "email_sender.py")
    
    # 1. Send News Briefing (Always)
    if os.path.exists(summarized_file):
        run_step("Email Distributor (News)", [python_exe, email_script, "-i", summarized_file, "--teams", team_emails_file], cwd=PROJECT_ROOT)
    
    # 2. Send Monitor Updates (Only if changes detected)
    if os.path.exists(monitor_file):
        try:
            with open(monitor_file, 'r', encoding='utf-8') as f:
                updates = json.load(f)
            
            if updates and len(updates) > 0:
                print(f"\n[INFO] {len(updates)} regulatory updates found. Sending alerts...")
                run_step("Email Distributor (Monitor)", [
                    python_exe, email_script, 
                    "-i", monitor_file, 
                    "--teams", team_emails_file,
                    "--monitor"
                ], cwd=PROJECT_ROOT)
            else:
                print("\n[INFO] No regulatory updates to report. Email skipped.")
                
        except Exception as e:
            print(f"[ERROR] Failed to check monitor file: {e}")
        
    # ---------------------------------------------------------
    # PART 4: SEND LOG EMAIL
    # ---------------------------------------------------------
    print("\n[PHASE 4] System Log Email")
    try:
        from src.email_sender import send_log_email
        send_log_email()
    except Exception as e:
        print(f"[ERROR] Log email failed: {e}")

    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
