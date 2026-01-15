#!/bin/bash
# 네이버 클라우드 서버 배포 스크립트
# Naver Cloud Server Deployment Script
# Ubuntu 20.04/22.04 기준

set -e  # 오류 발생 시 중단

echo "========================================="
echo "제약 뉴스 에이전트 - 네이버 클라우드 배포"
echo "Pharma News Agent - Naver Cloud Deploy"
echo "========================================="

# 1. 시스템 업데이트
echo "[1/8] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. Python 3.11 설치
echo "[2/8] Installing Python 3.11..."
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 3. 필수 시스템 패키지 설치
echo "[3/8] Installing system dependencies..."
sudo apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    git \
    curl \
    wget \
    cron

# 4. 작업 디렉토리 생성
echo "[4/8] Creating working directory..."
APP_DIR="/home/ubuntu/pharma_news_agent"
sudo mkdir -p $APP_DIR
sudo chown -R ubuntu:ubuntu $APP_DIR
cd $APP_DIR

# 5. Python 가상환경 생성
echo "[5/8] Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# 6. Python 패키지 설치
echo "[6/8] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 7. 환경변수 파일 생성 (수동으로 편집 필요)
echo "[7/8] Creating .env file template..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# API Keys (반드시 실제 키로 변경하세요!)
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Email Configuration
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Optional FDA API (더 많은 요청 허용)
OPENFDA_API_KEY=

# Environment
ENVIRONMENT=production
EOF
    echo "⚠️  .env 파일이 생성되었습니다. 실제 API 키로 수정하세요!"
    echo "⚠️  .env file created. Please edit with your actual API keys!"
else
    echo "✓ .env file already exists"
fi

# 8. 로그 디렉토리 생성
echo "[8/8] Creating log directories..."
mkdir -p logs
mkdir -p .ich_snapshots
mkdir -p .page_snapshots

# 실행 권한 부여
chmod +x run_pipeline.py
chmod +x multi_source_scraper.py

echo ""
echo "========================================="
echo "✓ 배포 완료!"
echo "✓ Deployment Complete!"
echo "========================================="
echo ""
echo "다음 단계:"
echo "1. .env 파일 편집: nano .env"
echo "2. team_emails.json 파일 업로드 (팀 이메일 목록)"
echo "3. 테스트 실행: source venv/bin/activate && python multi_source_scraper.py --days 1"
echo "4. Cron 작업 설정: sudo ./setup_cron.sh"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Upload team_emails.json (team email list)"
echo "3. Test run: source venv/bin/activate && python multi_source_scraper.py --days 1"
echo "4. Setup cron job: sudo ./setup_cron.sh"
