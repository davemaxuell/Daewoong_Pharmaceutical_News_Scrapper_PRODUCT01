@echo off
REM 제약 뉴스 에이전트 - 자동 실행 스크립트
REM Windows Task Scheduler에서 매일 자동으로 실행됩니다.
REM 
REM 파이프라인 단계:
REM   1. 뉴스 스크래핑 (KPA, Daily Pharm, Yakup, GMP Journal, ICH)
REM   2. 기사 본문 수집
REM   3. AI 요약 및 분류
REM   4. 팀별 이메일 발송

cd /d "%~dp0"

echo ============================================================
echo 제약 뉴스 에이전트 - 자동 수집 시작
echo 실행 시간: %date% %time%
echo ============================================================

REM 로그 디렉토리 생성
if not exist logs mkdir logs

REM 로그 파일 설정
set LOGFILE=logs\pipeline_%date:~0,4%%date:~5,2%%date:~8,2%.log

echo.
echo [옵션 선택]
echo   1. 전체 파이프라인 (스크래핑 + 요약 + 이메일)
echo   2. 스크래핑만 실행
echo.

REM 자동 실행 시 전체 파이프라인 실행 (옵션 없이)
if "%1"=="" (
    echo 자동 실행 모드: 전체 파이프라인
    goto :full_pipeline
)

if "%1"=="1" goto :full_pipeline
if "%1"=="2" goto :scrape_only
goto :full_pipeline

:full_pipeline
echo.
echo [전체 파이프라인 실행 중...]
echo.
call .venv\Scripts\python.exe run_pipeline.py 2>&1 | tee -a %LOGFILE%
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] 전체 파이프라인이 완료되었습니다.
) else (
    echo.
    echo [ERROR] 파이프라인 실행 중 오류가 발생했습니다.
)
goto :end

:scrape_only
echo.
echo [스크래핑만 실행 중...]
echo.
call .venv\Scripts\python.exe pharma_news_scraper.py 2>&1 | tee -a %LOGFILE%
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] 스크래핑이 완료되었습니다.
) else (
    echo.
    echo [ERROR] 스크래핑 중 오류가 발생했습니다.
)
goto :end

:end
echo.
echo ============================================================
echo 완료 시간: %date% %time%
echo 로그 파일: %LOGFILE%
echo ============================================================
