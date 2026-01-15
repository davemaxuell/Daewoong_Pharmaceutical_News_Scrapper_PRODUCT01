#!/bin/bash
# Cron 작업 설정 스크립트
# Setup Cron Job for Daily Automation

APP_DIR="/home/ubuntu/pharma_news_agent"
PYTHON_BIN="$APP_DIR/venv/bin/python"
SCRIPT_PATH="$APP_DIR/run_pipeline.py"
LOG_FILE="$APP_DIR/logs/cron_$(date +\%Y\%m\%d).log"

echo "========================================="
echo "Cron 작업 설정 (Daily News Pipeline)"
echo "========================================="

# Cron 작업 내용
CRON_JOB="0 7 * * * cd $APP_DIR && $PYTHON_BIN $SCRIPT_PATH >> $LOG_FILE 2>&1"

# 기존 cron 작업 확인
echo "현재 Cron 작업:"
crontab -l 2>/dev/null || echo "No existing cron jobs"

echo ""
echo "추가할 Cron 작업:"
echo "$CRON_JOB"
echo ""
echo "설명: 매일 오전 7시에 뉴스 수집 파이프라인 실행"
echo "Description: Run news pipeline daily at 7:00 AM KST"
echo ""

read -p "Cron 작업을 추가하시겠습니까? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 기존 cron에 추가
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

    echo "✓ Cron 작업이 추가되었습니다!"
    echo ""
    echo "현재 Cron 목록:"
    crontab -l
    echo ""
    echo "Cron 로그 위치: $APP_DIR/logs/"
    echo "Cron 작업 제거: crontab -e (해당 줄 삭제)"
else
    echo "취소되었습니다."
fi

echo ""
echo "========================================="
echo "수동 실행 방법:"
echo "cd $APP_DIR && source venv/bin/activate && python run_pipeline.py"
echo "========================================="
