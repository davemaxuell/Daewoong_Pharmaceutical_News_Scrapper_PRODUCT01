@echo off
REM Pharma News Agent - Main Launcher
REM Run the full pipeline from project root

echo ============================================================
echo Pharmaceutical News Agent - Full Pipeline
echo ============================================================

cd /d "%~dp0"
.\.venv\Scripts\python.exe src\run_pipeline.py %*

pause
