#!/bin/bash
# 자동화 문제 진단 스크립트
# Automation Diagnostics Script

echo "========================================="
echo "제약 뉴스 에이전트 - 자동화 진단"
echo "Pharma News Agent - Automation Diagnosis"
echo "========================================="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check Cron
echo "========================================"
echo "1. Cron Job Check"
echo "========================================"
if crontab -l 2>/dev/null | grep -q "pharma_news_agent"; then
    echo -e "${GREEN}✓ Cron job exists${NC}"
    echo ""
    echo "Cron configuration:"
    crontab -l | grep pharma_news_agent
else
    echo -e "${RED}✗ No cron job found${NC}"
    echo "Fix: cd /home/ubuntu/pharma_news_agent && ./setup_cron.sh"
fi
echo ""

# 2. Check Systemd
echo "========================================"
echo "2. Systemd Timer Check"
echo "========================================"
if systemctl list-timers 2>/dev/null | grep -q "pharma_news"; then
    echo -e "${GREEN}✓ Systemd timer configured${NC}"
    sudo systemctl status systemd_pharma_news.timer --no-pager
else
    echo -e "${YELLOW}ℹ Systemd timer not configured (OK if using cron)${NC}"
fi
echo ""

# 3. Check Timezone
echo "========================================"
echo "3. Timezone Check"
echo "========================================"
TIMEZONE=$(timedatectl | grep "Time zone" | awk '{print $3}')
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S %Z')

echo "Current timezone: $TIMEZONE"
echo "Current time: $CURRENT_TIME"

if [[ "$TIMEZONE" == "Asia/Seoul" ]]; then
    echo -e "${GREEN}✓ Timezone is correct (KST)${NC}"
else
    echo -e "${YELLOW}⚠ Timezone is not KST${NC}"
    echo "Fix: sudo timedatectl set-timezone Asia/Seoul"
    echo ""
    echo "If keeping UTC:"
    echo "  KST 07:00 = UTC 22:00 (previous day)"
fi
echo ""

# 4. Check Python environment
echo "========================================"
echo "4. Python Environment Check"
echo "========================================"
APP_DIR="/home/ubuntu/pharma_news_agent"

if [ -f "$APP_DIR/venv/bin/python" ]; then
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
    PYTHON_VERSION=$($APP_DIR/venv/bin/python --version 2>&1)
    echo "Python version: $PYTHON_VERSION"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "Fix: cd $APP_DIR && python3.11 -m venv venv"
fi
echo ""

# 5. Check .env file
echo "========================================"
echo "5. Environment Variables Check"
echo "========================================"
if [ -f "$APP_DIR/.env" ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"

    if grep -q "GEMINI_API_KEY=your_" "$APP_DIR/.env" 2>/dev/null; then
        echo -e "${YELLOW}⚠ GEMINI_API_KEY looks like placeholder${NC}"
    else
        echo -e "${GREEN}✓ GEMINI_API_KEY configured${NC}"
    fi

    if grep -q "EMAIL_SENDER=your_" "$APP_DIR/.env" 2>/dev/null; then
        echo -e "${YELLOW}⚠ EMAIL_SENDER looks like placeholder${NC}"
    else
        echo -e "${GREEN}✓ EMAIL_SENDER configured${NC}"
    fi
else
    echo -e "${RED}✗ .env file not found${NC}"
    echo "Fix: nano $APP_DIR/.env"
fi
echo ""

# 6. Check team_emails.json
echo "========================================"
echo "6. Email Configuration Check"
echo "========================================"
if [ -f "$APP_DIR/team_emails.json" ]; then
    echo -e "${GREEN}✓ team_emails.json exists${NC}"
else
    echo -e "${YELLOW}⚠ team_emails.json not found${NC}"
    echo "Upload team_emails.json to $APP_DIR/"
fi
echo ""

# 7. Check logs directory
echo "========================================"
echo "7. Logs Directory Check"
echo "========================================"
if [ -d "$APP_DIR/logs" ]; then
    echo -e "${GREEN}✓ Logs directory exists${NC}"
    LOG_COUNT=$(ls -1 "$APP_DIR/logs" 2>/dev/null | wc -l)
    echo "Number of log files: $LOG_COUNT"

    # Check permissions
    LOG_OWNER=$(ls -ld "$APP_DIR/logs" | awk '{print $3":"$4}')
    echo "Owner: $LOG_OWNER"

    if [[ "$LOG_OWNER" != "ubuntu:ubuntu" ]]; then
        echo -e "${YELLOW}⚠ Ownership issue detected${NC}"
        echo "Fix: sudo chown -R ubuntu:ubuntu $APP_DIR/logs/"
    fi

    # Show recent logs
    echo ""
    echo "Recent log files:"
    ls -lht "$APP_DIR/logs" | head -5
else
    echo -e "${RED}✗ Logs directory not found${NC}"
    echo "Fix: mkdir -p $APP_DIR/logs"
fi
echo ""

# 8. Check recent execution
echo "========================================"
echo "8. Recent Execution Check"
echo "========================================"
TODAY=$(date +%Y%m%d)
if [ -f "$APP_DIR/logs/cron_$TODAY.log" ]; then
    echo -e "${GREEN}✓ Today's log file exists${NC}"
    LOG_SIZE=$(du -h "$APP_DIR/logs/cron_$TODAY.log" | cut -f1)
    echo "Log file size: $LOG_SIZE"
    echo ""
    echo "Last 10 lines:"
    tail -10 "$APP_DIR/logs/cron_$TODAY.log"
else
    echo -e "${YELLOW}ℹ No log for today (pipeline hasn't run yet)${NC}"

    # Check yesterday's log
    YESTERDAY=$(date -d "yesterday" +%Y%m%d 2>/dev/null || date -v-1d +%Y%m%d 2>/dev/null)
    if [ -f "$APP_DIR/logs/cron_$YESTERDAY.log" ]; then
        echo ""
        echo "Yesterday's log exists. Last 5 lines:"
        tail -5 "$APP_DIR/logs/cron_$YESTERDAY.log"
    fi
fi
echo ""

# 9. Check system cron log
echo "========================================"
echo "9. System Cron Log Check"
echo "========================================"
echo "Recent cron executions for this user:"
sudo grep "$(whoami).*pharma" /var/log/syslog 2>/dev/null | tail -5 || \
    echo "No recent cron executions found in syslog"
echo ""

# 10. Test manual execution
echo "========================================"
echo "10. Manual Execution Test"
echo "========================================"
echo "Testing if pipeline can run manually..."

if [ -f "$APP_DIR/run_pipeline.py" ]; then
    echo "Command that would be executed:"
    echo "cd $APP_DIR && $APP_DIR/venv/bin/python $APP_DIR/run_pipeline.py"
    echo ""
    echo "Do you want to test it now? (y/n)"
    read -t 5 -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd $APP_DIR
        $APP_DIR/venv/bin/python $APP_DIR/run_pipeline.py
    else
        echo "Skipped manual test"
    fi
else
    echo -e "${RED}✗ run_pipeline.py not found${NC}"
fi
echo ""

# Summary
echo "========================================="
echo "SUMMARY"
echo "========================================="
echo ""

# Count issues
ISSUES=0

if ! crontab -l 2>/dev/null | grep -q "pharma_news_agent"; then
    echo -e "${RED}[ISSUE]${NC} Cron job not configured"
    ISSUES=$((ISSUES+1))
fi

if [[ "$TIMEZONE" != "Asia/Seoul" ]]; then
    echo -e "${YELLOW}[WARNING]${NC} Timezone not KST"
fi

if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${RED}[ISSUE]${NC} .env file missing"
    ISSUES=$((ISSUES+1))
fi

if [ ! -f "$APP_DIR/team_emails.json" ]; then
    echo -e "${YELLOW}[WARNING]${NC} team_emails.json missing"
fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ No critical issues found!${NC}"
    echo ""
    echo "The system should run automatically at 07:00 KST"
    echo "Check logs: tail -f $APP_DIR/logs/cron_\$(date +%Y%m%d).log"
else
    echo -e "${RED}Found $ISSUES critical issue(s)${NC}"
    echo ""
    echo "Quick fix:"
    echo "1. sudo timedatectl set-timezone Asia/Seoul"
    echo "2. cd $APP_DIR && ./setup_cron.sh"
    echo "3. nano $APP_DIR/.env (add API keys)"
fi

echo ""
echo "========================================="
echo "For more help, see: TROUBLESHOOT_AUTOMATION.md"
echo "========================================="
