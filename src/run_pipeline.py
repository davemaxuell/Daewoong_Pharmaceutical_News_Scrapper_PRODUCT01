# 제약 뉴스 에이전트 - 통합 파이프라인
# 1. 뉴스 스크래핑 및 요약 (Gemini)
# 2. 규제 모니터링 및 PDF 분석 (Gemini)
# 3. 이메일 발송

import subprocess
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
import glob
import json
import atexit

# Get the project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_NEWS_DIR = os.path.join(PROJECT_ROOT, "data", "news")
DATA_MONITORS_DIR = os.path.join(PROJECT_ROOT, "data", "monitors")
DATA_DIAGNOSTICS_DIR = os.path.join(PROJECT_ROOT, "data", "diagnostics")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# Ensure data directories exist
os.makedirs(DATA_NEWS_DIR, exist_ok=True)
os.makedirs(DATA_MONITORS_DIR, exist_ok=True)
os.makedirs(DATA_DIAGNOSTICS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

from src.env_config import load_project_env
from src.runtime_admin_config import load_runtime_admin_config, record_schedule_run

# Load .env from project root or config directory
load_project_env()


class _TeeStream:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for stream in self._streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self._streams:
            stream.flush()


def setup_pipeline_logging() -> str:
    """Mirror pipeline stdout/stderr to the daily cron log."""
    today = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(LOGS_DIR, f"cron_{today}.log")
    log_handle = open(log_path, "a", encoding="utf-8")
    sys.stdout = _TeeStream(sys.__stdout__, log_handle)
    sys.stderr = _TeeStream(sys.__stderr__, log_handle)
    atexit.register(log_handle.close)
    return log_path


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
        os.path.join(DATA_DIAGNOSTICS_DIR, "latest_sources_*.json"),
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


def parse_args():
    parser = argparse.ArgumentParser(description="Run the full pharma news pipeline.")
    parser.add_argument(
        "--ignore-db-schedule",
        action="store_true",
        help="Run even when the admin DB schedule is disabled (used for manual admin-triggered runs).",
    )
    return parser.parse_args()


def main(ignore_db_schedule: bool = False):
    log_path = setup_pipeline_logging()
    print("""
================================================================
       Pharmaceutical News Agent - Full Pipeline (v2.0)
================================================================
    """)

    now = datetime.now()
    weekday = now.weekday()
    is_weekend = weekday >= 5
    is_monday = weekday == 0
    today = now.strftime('%Y%m%d')
    failed_steps = []
    days_back = 3 if is_monday else 1

    if is_weekend:
        day_label = "Weekend"
    elif is_monday:
        day_label = "Monday"
    else:
        day_label = "Weekday"

    print(f"Date: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Day: {day_label}")
    print(f"Days back: {days_back}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Log file: {log_path}")

    # Cleanup old files (older than 14 days)
    cleanup_old_files(days_old=14)

    runtime_admin_config = load_runtime_admin_config()
    schedule_settings = runtime_admin_config.get("schedule", {}) if isinstance(runtime_admin_config, dict) else {}
    if schedule_settings:
        print(
            f"DB schedule: {schedule_settings.get('cron_expr') or '-'} "
            f"({schedule_settings.get('timezone') or 'Asia/Seoul'}) | enabled={schedule_settings.get('is_enabled')}"
        )

    if schedule_settings and not schedule_settings.get("is_enabled", True) and not ignore_db_schedule:
        print("\n[INFO] Admin DB schedule is disabled. Skipping scheduled pipeline run.")
        return 0

    # Check minimum run frequency (scrape_frequency_minutes from admin general settings)
    if not ignore_db_schedule and isinstance(runtime_admin_config, dict):
        general_settings = runtime_admin_config.get("general", {}) or {}
        frequency_minutes = general_settings.get("scrape_frequency_minutes")
        last_run_at_str = (schedule_settings or {}).get("last_run_at")
        if frequency_minutes and last_run_at_str:
            try:
                last_run_at = datetime.fromisoformat(last_run_at_str)
                if last_run_at.tzinfo is None:
                    last_run_at = last_run_at.replace(tzinfo=timezone.utc)
                elapsed_minutes = (datetime.now(timezone.utc) - last_run_at).total_seconds() / 60
                if elapsed_minutes < frequency_minutes:
                    print(
                        f"\n[INFO] Last run was {elapsed_minutes:.0f} min ago. "
                        f"Min frequency is {frequency_minutes} min. Skipping."
                    )
                    return 0
            except Exception as exc:
                print(f"[WARN] Could not check run frequency: {exc}")

    # Stamp last_run_at now so concurrent cron triggers see it immediately
    record_schedule_run()

    if is_weekend:
        print("\n[INFO] Weekend run detected. Pipeline will not scrape or send emails on Saturday/Sunday.")
        print("[INFO] Monday runs automatically collect the last 3 days, so weekend news will be included then.")
        return 0

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
        failed_steps.append("Multi-Source Scraper")

    # 2. AI Summarization (Gemini) - directly on news file (now has full_text)
    summarizer_script = os.path.join(SRC_DIR, "ai_summarizer_gemini.py")
    if os.path.exists(news_file):
        if not run_step("AI Summarizer (Gemini)", [python_exe, summarizer_script, "-i", news_file, "-o", summarized_file], cwd=PROJECT_ROOT):
            failed_steps.append("AI Summarizer (Gemini)")
    else:
        print(f"[ERROR] News file {news_file} not found. Skipping AI summarization.")
        failed_steps.append("AI Summarizer (Gemini) - input missing")

    # ---------------------------------------------------------
    # PART 2: MONITOR PIPELINE
    # ---------------------------------------------------------
    print("\n[PHASE 2] Regulatory Monitoring")
    
    # ICH & PDF Monitor Pipeline
    monitor_script = os.path.join(SRC_DIR, "monitor_pipeline.py")
    if not run_step("ICH & PDF Monitor", [python_exe, monitor_script], cwd=PROJECT_ROOT):
        failed_steps.append("ICH & PDF Monitor")

    diagnostic_script = os.path.join(PROJECT_ROOT, "scripts", "diagnose_latest_sources.py")
    if not run_step("Source Health Diagnostics", [python_exe, diagnostic_script, "--days", str(days_back)], cwd=PROJECT_ROOT):
        failed_steps.append("Source Health Diagnostics")

    # ---------------------------------------------------------
    # PART 3: REPORTING
    # ---------------------------------------------------------
    print("\n[PHASE 3] Reporting")
    
    email_script = os.path.join(SRC_DIR, "email_sender.py")
    
    # 1. Send News Briefing (Always)
    if os.path.exists(summarized_file):
        if not run_step("Email Distributor (News)", [python_exe, email_script, "-i", summarized_file, "--teams", team_emails_file], cwd=PROJECT_ROOT):
            failed_steps.append("Email Distributor (News)")
    
    # 2. Send Monitor Updates (Only if changes detected)
    if os.path.exists(monitor_file):
        try:
            with open(monitor_file, 'r', encoding='utf-8') as f:
                updates = json.load(f)
            
            if updates and len(updates) > 0:
                print(f"\n[INFO] {len(updates)} regulatory updates found. Sending alerts...")
                if not run_step("Email Distributor (Monitor)", [
                    python_exe, email_script, 
                    "-i", monitor_file, 
                    "--teams", team_emails_file,
                    "--monitor"
                ], cwd=PROJECT_ROOT):
                    failed_steps.append("Email Distributor (Monitor)")
            else:
                print("\n[INFO] No regulatory updates to report. Email skipped.")
                
        except Exception as e:
            print(f"[ERROR] Failed to check monitor file: {e}")
        
    # ---------------------------------------------------------
    # PART 4: SEND ADMIN EMAILS
    # ---------------------------------------------------------
    print("\n[PHASE 4] Admin Emails")
    try:
        from src.email_sender import send_admin_summary_email, send_log_email
        if not send_log_email(log_path):
            failed_steps.append("System Log Email")
        if not send_admin_summary_email():
            failed_steps.append("Daily Admin Summary Email")
    except Exception as e:
        print(f"[ERROR] Admin email step failed: {e}")
        failed_steps.append("Admin Emails")

    if failed_steps:
        print("\n[FINAL] Pipeline completed with failures.")
        print("[FINAL] Failed steps:")
        for step in failed_steps:
            print(f"  - {step}")
        return 1

    print("\n[FINAL] All tasks completed successfully.")
    return 0

if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main(ignore_db_schedule=args.ignore_db_schedule))
