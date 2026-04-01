#!/bin/bash
# Systemd 서비스 및 타이머 설정 스크립트
# Setup Systemd Service and Timer

set -e

echo "========================================="
echo "Systemd 서비스 설정"
echo "Setup Systemd Service & Timer"
echo "========================================="

# systemd 파일 복사
echo "[1/4] Copying systemd files..."
sudo cp systemd_pharma_news.service /etc/systemd/system/
sudo cp systemd_pharma_news.timer /etc/systemd/system/

# 권한 설정
echo "[2/4] Setting permissions..."
sudo chmod 644 /etc/systemd/system/systemd_pharma_news.service
sudo chmod 644 /etc/systemd/system/systemd_pharma_news.timer

# systemd 데몬 리로드
echo "[3/4] Reloading systemd daemon..."
sudo systemctl daemon-reload

# 타이머 활성화 및 시작
echo "[4/4] Enabling and starting timer..."
sudo systemctl enable systemd_pharma_news.timer
sudo systemctl start systemd_pharma_news.timer

echo ""
echo "========================================="
echo "✓ Systemd 설정 완료!"
echo "✓ Systemd Setup Complete!"
echo "========================================="
echo ""
echo "유용한 명령어:"
echo ""
echo "# 타이머 상태 확인"
echo "sudo systemctl status systemd_pharma_news.timer"
echo ""
echo "# 다음 실행 시간 확인"
echo "sudo systemctl list-timers systemd_pharma_news.timer"
echo ""
echo "# 수동 실행 (테스트)"
echo "sudo systemctl start systemd_pharma_news.service"
echo ""
echo "# 로그 확인"
echo "sudo journalctl -u systemd_pharma_news.service -f"
echo "tail -f logs/systemd_output.log"
echo ""
echo "# 타이머 중지/시작"
echo "sudo systemctl stop systemd_pharma_news.timer"
echo "sudo systemctl start systemd_pharma_news.timer"
echo ""

# 현재 상태 표시
echo "현재 타이머 상태:"
sudo systemctl status systemd_pharma_news.timer --no-pager
