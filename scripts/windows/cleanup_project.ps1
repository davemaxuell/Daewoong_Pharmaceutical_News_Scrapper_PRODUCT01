# =====================================================
# Project Cleanup Script (Windows PowerShell)
# Removes duplicate and unnecessary files
# =====================================================
# Run with: .\cleanup_project.ps1
# =====================================================

$ErrorActionPreference = "Stop"

Write-Host "=" * 60
Write-Host "Project Cleanup Script"
Write-Host "=" * 60

$projectRoot = $PSScriptRoot

# === 1. DUPLICATE FILES IN /scrapers (already exist in root) ===
Write-Host "`n[1] Removing duplicate files in /scrapers folder..."

$duplicatesInScrapers = @(
    "scrapers\ai_summarizer.py",
    "scrapers\ai_summarizer_gemini.py",
    "scrapers\content_scraper.py",
    "scrapers\email_sender.py",
    "scrapers\health_check.py",
    "scrapers\html_change_monitor.py",
    "scrapers\ich_monitor.py",
    "scrapers\keywords.py",
    "scrapers\logger.py",
    "scrapers\monitor_pipeline.py",
    "scrapers\multi_source_scraper.py",
    "scrapers\pharma_news_scraper.py",
    "scrapers\run_pipeline.py",
    "scrapers\team_definitions.py",
    "scrapers\README.md",
    "scrapers\NAVER_CLOUD_DEPLOYMENT_GUIDE.md",
    "scrapers\QUICK_START_NAVER_CLOUD.md",
    "scrapers\requirements.txt",
    "scrapers\deploy_naver_cloud.sh",
    "scrapers\run_pipeline_linux.sh",
    "scrapers\setup_cron.sh",
    "scrapers\setup_systemd.sh"
)

foreach ($file in $duplicatesInScrapers) {
    $fullPath = Join-Path $projectRoot $file
    if (Test-Path $fullPath) {
        Remove-Item $fullPath -Force
        Write-Host "  [DELETED] $file"
    }
}

# === 2. TEST FILES (development only) ===
Write-Host "`n[2] Removing test files..."

$testFiles = @(
    "test.py",
    "test_gemini_migration.py",
    "test_kpanews_scraper.py",
    "test_kpbma_scraper.py",
    "test_mfds_scraper.py",
    "test_pipeline_flow.py",
    "test_pmda_scraper.py",
    "test_usp_scraper.py",
    "scrapers\test.py",
    "scrapers\test_gemini_migration.py",
    "scrapers\test_kpanews_scraper.py",
    "scrapers\test_kpbma_scraper.py",
    "scrapers\test_mfds_scraper.py",
    "scrapers\test_pipeline_flow.py",
    "scrapers\test_pmda_scraper.py",
    "scrapers\test_usp_scraper.py"
)

foreach ($file in $testFiles) {
    $fullPath = Join-Path $projectRoot $file
    if (Test-Path $fullPath) {
        Remove-Item $fullPath -Force
        Write-Host "  [DELETED] $file"
    }
}

# === 3. TEST/SAMPLE JSON FILES ===
Write-Host "`n[3] Removing test/sample JSON files..."

$testJsonFiles = @(
    "edqm_test.json",
    "eudralex_sample.json",
    "mfds_test.json",
    "usp_rb_test.json",
    "usp_test_output.json",
    "test_gemini_output.json",
    "test_summary.json"
)

foreach ($file in $testJsonFiles) {
    $fullPath = Join-Path $projectRoot $file
    if (Test-Path $fullPath) {
        Remove-Item $fullPath -Force
        Write-Host "  [DELETED] $file"
    }
}

# === 4. LEGACY FILES (replaced by newer versions) ===
Write-Host "`n[4] Removing legacy files..."

$legacyFiles = @(
    "ai_summarizer.py",       # Replaced by ai_summarizer_gemini.py
    "content_scraper.py",     # Scrapers now fetch content directly
    "pharma_news_scraper.py"  # Replaced by multi_source_scraper.py
)

foreach ($file in $legacyFiles) {
    $fullPath = Join-Path $projectRoot $file
    if (Test-Path $fullPath) {
        Remove-Item $fullPath -Force
        Write-Host "  [DELETED] $file"
    }
}

# === 5. OLD DATED JSON FILES (older than 7 days) ===
Write-Host "`n[5] Removing old dated JSON files..."

$cutoffDate = (Get-Date).AddDays(-7)
$jsonPatterns = @("multi_source_*.json", "monitor_updates_*.json", "pharma_news_*.json")

foreach ($pattern in $jsonPatterns) {
    Get-ChildItem -Path $projectRoot -Filter $pattern -File | ForEach-Object {
        if ($_.LastWriteTime -lt $cutoffDate) {
            Remove-Item $_.FullName -Force
            Write-Host "  [DELETED] $($_.Name)"
        }
    }
}

Write-Host "`n" + "=" * 60
Write-Host "[CLEANUP COMPLETE]"
Write-Host "=" * 60
