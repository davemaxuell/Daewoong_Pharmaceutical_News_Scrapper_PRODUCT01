#!/bin/bash
# =====================================================
# Project Cleanup Script (Linux/Cloud Server)
# Removes duplicate and unnecessary files
# =====================================================
# Run with: chmod +x cleanup_project.sh && ./cleanup_project.sh
# =====================================================

set -e

echo "============================================================"
echo "Project Cleanup Script"
echo "============================================================"

cd "$(dirname "$0")"

# === 1. DUPLICATE FILES IN /scrapers (already exist in root) ===
echo ""
echo "[1] Removing duplicate files in /scrapers folder..."

DUPLICATES=(
    "scrapers/ai_summarizer.py"
    "scrapers/ai_summarizer_gemini.py"
    "scrapers/content_scraper.py"
    "scrapers/email_sender.py"
    "scrapers/health_check.py"
    "scrapers/html_change_monitor.py"
    "scrapers/ich_monitor.py"
    "scrapers/keywords.py"
    "scrapers/logger.py"
    "scrapers/monitor_pipeline.py"
    "scrapers/multi_source_scraper.py"
    "scrapers/pharma_news_scraper.py"
    "scrapers/run_pipeline.py"
    "scrapers/team_definitions.py"
    "scrapers/README.md"
    "scrapers/NAVER_CLOUD_DEPLOYMENT_GUIDE.md"
    "scrapers/QUICK_START_NAVER_CLOUD.md"
    "scrapers/requirements.txt"
    "scrapers/deploy_naver_cloud.sh"
    "scrapers/run_pipeline_linux.sh"
    "scrapers/setup_cron.sh"
    "scrapers/setup_systemd.sh"
)

for file in "${DUPLICATES[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  [DELETED] $file"
    fi
done

# === 2. TEST FILES (development only) ===
echo ""
echo "[2] Removing test files..."

TEST_FILES=(
    "test.py"
    "test_gemini_migration.py"
    "test_kpanews_scraper.py"
    "test_kpbma_scraper.py"
    "test_mfds_scraper.py"
    "test_pipeline_flow.py"
    "test_pmda_scraper.py"
    "test_usp_scraper.py"
    "scrapers/test.py"
    "scrapers/test_gemini_migration.py"
    "scrapers/test_kpanews_scraper.py"
    "scrapers/test_kpbma_scraper.py"
    "scrapers/test_mfds_scraper.py"
    "scrapers/test_pipeline_flow.py"
    "scrapers/test_pmda_scraper.py"
    "scrapers/test_usp_scraper.py"
)

for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  [DELETED] $file"
    fi
done

# === 3. TEST/SAMPLE JSON FILES ===
echo ""
echo "[3] Removing test/sample JSON files..."

TEST_JSON=(
    "edqm_test.json"
    "eudralex_sample.json"
    "mfds_test.json"
    "usp_rb_test.json"
    "usp_test_output.json"
    "test_gemini_output.json"
    "test_summary.json"
)

for file in "${TEST_JSON[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  [DELETED] $file"
    fi
done

# === 4. LEGACY FILES (replaced by newer versions) ===
echo ""
echo "[4] Removing legacy files..."

LEGACY_FILES=(
    "ai_summarizer.py"        # Replaced by ai_summarizer_gemini.py
    "content_scraper.py"      # Scrapers now fetch content directly
    "pharma_news_scraper.py"  # Replaced by multi_source_scraper.py
)

for file in "${LEGACY_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  [DELETED] $file"
    fi
done

# === 5. OLD DATED JSON FILES (older than 7 days) ===
echo ""
echo "[5] Removing old dated JSON files (older than 7 days)..."

find . -maxdepth 1 -name "multi_source_*.json" -mtime +7 -exec rm -f {} \; -exec echo "  [DELETED] {}" \;
find . -maxdepth 1 -name "monitor_updates_*.json" -mtime +7 -exec rm -f {} \; -exec echo "  [DELETED] {}" \;
find . -maxdepth 1 -name "pharma_news_*.json" -mtime +7 -exec rm -f {} \; -exec echo "  [DELETED] {}" \;

echo ""
echo "============================================================"
echo "[CLEANUP COMPLETE]"
echo "============================================================"
