# 🚀 네이버 클라우드 배포 가이드
# Naver Cloud Platform Deployment Guide

## 📋 목차 / Table of Contents

1. [사전 준비](#사전-준비)
2. [네이버 클라우드 서버 생성](#네이버-클라우드-서버-생성)
3. [파일 업로드](#파일-업로드)
4. [서버 설정](#서버-설정)
5. [자동화 설정](#자동화-설정)
6. [테스트 및 모니터링](#테스트-및-모니터링)
7. [문제 해결](#문제-해결)

---

## 🎯 사전 준비

### 1. 네이버 클라우드 계정
- [https://www.ncloud.com](https://www.ncloud.com) 회원가입
- 결제 수단 등록 (신용카드)
- 초기 크레딧 활용 가능

### 2. 필요한 정보 준비
```bash
# API Keys (반드시 필요!)
✓ OpenAI API Key (백업용)
✓ Google Gemini API Key (메인 AI)
✓ Gmail 계정 및 앱 비밀번호

# 선택사항
□ FDA API Key (요청 제한 완화)
```

### 3. 로컬 파일 확인
```bash
cd "제약 뉴스 에이전트"

# 필수 파일 목록
✓ requirements.txt
✓ .env (API 키 포함)
✓ team_emails.json
✓ 모든 Python 파일 (.py)
✓ scrapers/ 폴더
✓ keywords.py
✓ team_definitions.py
```

---

## 🖥️ 네이버 클라우드 서버 생성

### Step 1: Server 생성

1. **네이버 클라우드 콘솔 접속**
   - Console > Services > Compute > Server

2. **서버 생성 버튼 클릭**
   - "서버 생성" 또는 "Create Server"

3. **서버 이미지 선택**
   ```
   OS: Ubuntu Server 22.04 LTS (64-bit)
   ```

4. **서버 타입 선택**
   ```
   추천:
   - Compact: 2 vCPU, 4GB RAM (월 약 2만원)
   - Standard: 2 vCPU, 8GB RAM (월 약 4만원)

   최소 사양:
   - Micro: 1 vCPU, 1GB RAM (테스트용)
   ```

5. **스토리지 설정**
   ```
   50GB SSD (기본값으로 충분)
   ```

6. **네트워크 설정**
   - VPC: 기본 VPC 사용
   - Subnet: 기본 Subnet 사용
   - **Public IP: 할당** (필수!)

7. **인증키 설정**
   - 새 인증키 생성
   - **중요**: 생성된 .pem 파일 다운로드 및 안전하게 보관

8. **ACG (방화벽) 설정**
   ```
   인바운드 규칙 추가:
   - SSH: TCP 22 (접속용)
   - HTTP: TCP 80 (선택사항)
   - HTTPS: TCP 443 (선택사항)

   소스: My IP 또는 특정 IP만 허용 (보안)
   ```

9. **서버 생성 완료**
   - 생성 시간: 약 2-3분
   - Public IP 확인 및 메모

---

## 📤 파일 업로드

### Option 1: SCP 사용 (Windows)

```powershell
# PowerShell에서 실행

# 1. .pem 키 권한 설정
icacls "C:\path\to\your-key.pem" /inheritance:r
icacls "C:\path\to\your-key.pem" /grant:r "%username%:R"

# 2. 전체 프로젝트 폴더 업로드
scp -i "C:\path\to\your-key.pem" -r "C:\Users\user\Desktop\제약 뉴스 에이전트\*" ubuntu@YOUR_SERVER_IP:/home/ubuntu/pharma_news_agent/

# YOUR_SERVER_IP를 실제 서버 Public IP로 변경
```

### Option 2: WinSCP 사용 (GUI 방식)

1. **WinSCP 다운로드**
   - https://winscp.net/download/WinSCP-Setup.exe

2. **연결 설정**
   ```
   파일 프로토콜: SFTP
   호스트 이름: YOUR_SERVER_IP
   포트 번호: 22
   사용자 이름: ubuntu
   비밀번호: (사용 안 함)
   개인 키 파일: your-key.pem
   ```

3. **파일 드래그 앤 드롭**
   - 로컬: `제약 뉴스 에이전트` 폴더
   - 서버: `/home/ubuntu/pharma_news_agent/`

### Option 3: Git 사용 (추천)

```bash
# 로컬에서 Git 저장소 생성 (한번만)
cd "제약 뉴스 에이전트"
git init
git add .
git commit -m "Initial commit"

# GitHub Private Repository에 푸시
# (민감한 정보 제외: .env, team_emails.json)

# 서버에서 클론
ssh -i your-key.pem ubuntu@YOUR_SERVER_IP
git clone https://github.com/your-username/pharma-news-agent.git pharma_news_agent
```

---

## ⚙️ 서버 설정

### Step 1: SSH 접속

```bash
# Windows PowerShell 또는 Git Bash
ssh -i "path\to\your-key.pem" ubuntu@YOUR_SERVER_IP

# 성공 시
ubuntu@naver-cloud:~$
```

### Step 2: 자동 배포 스크립트 실행

```bash
cd /home/ubuntu/pharma_news_agent

# 실행 권한 부여
chmod +x deploy_naver_cloud.sh

# 배포 스크립트 실행
./deploy_naver_cloud.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- ✓ 시스템 패키지 업데이트
- ✓ Python 3.11 설치
- ✓ 필수 라이브러리 설치
- ✓ 가상환경 생성
- ✓ Python 패키지 설치
- ✓ .env 템플릿 생성

### Step 3: 환경변수 설정

```bash
# .env 파일 편집
nano .env
```

다음 내용을 **실제 값으로 변경**:

```bash
# API Keys
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxx

# Email Configuration
EMAIL_SENDER=your_actual_email@gmail.com
EMAIL_PASSWORD=your_16_digit_app_password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Optional
OPENFDA_API_KEY=

# Environment
ENVIRONMENT=production
```

**저장**: `Ctrl + X` → `Y` → `Enter`

### Step 4: 팀 이메일 파일 업로드

```bash
# team_emails.json이 없으면 수동으로 생성
nano team_emails.json
```

내용 예시:
```json
{
  "해외사업": ["overseas@company.com"],
  "영업": ["sales@company.com"],
  "R&D": ["rd@company.com"],
  "마케팅": ["marketing@company.com"],
  "경영지원": ["admin@company.com"],
  "RA": ["ra@company.com"]
}
```

---

## 🤖 자동화 설정

### Option A: Cron 사용 (간단, 추천)

```bash
# Cron 설정 스크립트 실행
chmod +x setup_cron.sh
./setup_cron.sh

# 확인
crontab -l

# 출력 예시:
# 0 7 * * * cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py >> /home/ubuntu/pharma_news_agent/logs/cron_$(date +\%Y\%m\%d).log 2>&1
```

**실행 시간**: 매일 오전 7시 (KST)

**Cron 수정**:
```bash
crontab -e

# 다른 시간으로 변경 예시:
# 0 9 * * * ... (오전 9시)
# 0 6 * * 1-5 ... (평일 오전 6시)
```

### Option B: Systemd 사용 (고급)

```bash
# Systemd 설정 스크립트 실행
chmod +x setup_systemd.sh
sudo ./setup_systemd.sh

# 상태 확인
sudo systemctl status systemd_pharma_news.timer

# 다음 실행 시간 확인
sudo systemctl list-timers systemd_pharma_news.timer
```

**장점**:
- 로그 관리 용이
- 서비스 재시작 자동화
- 상태 모니터링 쉬움

---

## 🧪 테스트 및 모니터링

### Step 1: 수동 테스트

```bash
cd /home/ubuntu/pharma_news_agent

# 가상환경 활성화
source venv/bin/activate

# 테스트 1: 스크래퍼만 실행 (1일치)
python multi_source_scraper.py --days 1 -o test_output.json

# 성공 시: test_output.json 생성됨
cat test_output.json | head -50

# 테스트 2: AI 요약 (비용 발생 주의!)
python ai_summarizer_gemini.py -i test_output.json -o test_summarized.json

# 테스트 3: 전체 파이프라인 (이메일 발송됨!)
python run_pipeline.py
```

### Step 2: 로그 확인

```bash
# 최신 로그 확인
ls -lht logs/

# Cron 로그 실시간 확인
tail -f logs/cron_$(date +%Y%m%d).log

# Systemd 로그 확인
sudo journalctl -u systemd_pharma_news.service -f
tail -f logs/systemd_output.log
```

### Step 3: 출력 파일 확인

```bash
# 오늘 생성된 파일
ls -lh multi_source_*$(date +%Y%m%d).json

# 파일 내용 미리보기
cat multi_source_summarized_$(date +%Y%m%d).json | head -100
```

---

## 🔍 문제 해결

### 문제 1: Python 패키지 설치 실패

```bash
# pip 업그레이드
source venv/bin/activate
pip install --upgrade pip

# 개별 패키지 재설치
pip install beautifulsoup4 requests google-generativeai --force-reinstall
```

### 문제 2: 이메일 발송 실패

```bash
# Gmail 앱 비밀번호 확인
# https://myaccount.google.com/apppasswords

# SMTP 테스트
python -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('Test')
msg['Subject'] = 'Test from Naver Cloud'
msg['From'] = 'your_email@gmail.com'
msg['To'] = 'your_email@gmail.com'

with smtplib.SMTP('smtp.gmail.com', 587) as server:
    server.starttls()
    server.login('your_email@gmail.com', 'your_app_password')
    server.send_message(msg)
    print('Email sent successfully!')
"
```

### 문제 3: 메모리 부족

```bash
# 메모리 확인
free -h

# 스왑 메모리 추가 (2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구적으로 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 문제 4: FDA 스크래핑 실패

```bash
# FDA API가 응답하는지 확인
curl "https://api.fda.gov/drug/enforcement.json?limit=1"

# FDA 스크래퍼 개별 테스트
python scrapers/fda_warning_scraper.py --days 7
```

### 문제 5: Gemini API 오류

```bash
# API 키 확인
cat .env | grep GEMINI

# Gemini API 테스트
python -c "
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')
response = model.generate_content('Hello!')
print(response.text)
"
```

---

## 📊 모니터링 및 유지보수

### 일일 체크리스트

```bash
# 1. 로그 확인
tail -50 logs/cron_$(date +%Y%m%d).log

# 2. 오늘 생성된 파일 확인
ls -lh *$(date +%Y%m%d).json

# 3. 디스크 사용량 확인
df -h

# 4. 프로세스 확인
ps aux | grep python
```

### 주간 유지보수

```bash
# 1. 오래된 로그 파일 정리 (30일 이상)
find logs/ -name "*.log" -mtime +30 -delete

# 2. 오래된 JSON 파일 정리 (30일 이상)
find . -name "*_2025*.json" -mtime +30 -delete

# 3. 시스템 업데이트
sudo apt-get update && sudo apt-get upgrade -y

# 4. Python 패키지 업데이트 (선택)
source venv/bin/activate
pip list --outdated
```

### 백업

```bash
# 중요 파일 백업 (Naver Object Storage 사용 권장)
tar -czf pharma_news_backup_$(date +%Y%m%d).tar.gz \
    .env \
    team_emails.json \
    *.py \
    scrapers/ \
    requirements.txt

# 로컬로 다운로드 (Windows)
scp -i your-key.pem ubuntu@YOUR_SERVER_IP:/home/ubuntu/pharma_news_agent/pharma_news_backup_*.tar.gz .
```

---

## 💰 예상 비용

### 네이버 클라우드 (월간)

| 항목 | 사양 | 월 비용 |
|------|------|---------|
| Server (Compact) | 2 vCPU, 4GB RAM | ₩20,000 |
| Public IP | 1개 | ₩3,000 |
| Storage | 50GB SSD | 포함 |
| 트래픽 | ~10GB/월 | 무료 |
| **합계** | | **₩23,000** |

### API 비용 (월간 예상)

| 서비스 | 사용량 | 월 비용 |
|--------|--------|---------|
| Gemini 2.0 Flash | 200 기사/일 × 30일 | 무료 (할당량 내) |
| OpenAI GPT-4o-mini | 백업용 | $0 |
| Gmail SMTP | 무제한 | 무료 |
| openFDA API | 무제한 | 무료 |
| **합계** | | **$0** |

**총 월 비용**: 약 **₩23,000** (네이버 클라우드만)

---

## 🎓 고급 기능 (선택사항)

### 1. Naver Object Storage 연동

```bash
# AWS S3 호환 API 사용
pip install boto3

# 매일 결과 파일을 Object Storage에 백업
# backup_to_storage.py 생성 필요
```

### 2. Naver Cloud Monitoring 설정

```
Console > Management > Cloud Monitoring
- CPU 사용률 알림: 80% 이상
- 메모리 사용률 알림: 90% 이상
- 디스크 사용률 알림: 80% 이상
```

### 3. Load Balancer (확장 시)

```
여러 서버로 확장 시:
- Load Balancer 설정
- Auto Scaling 그룹 생성
- Health Check 구성
```

---

## 📞 지원 및 문의

### 네이버 클라우드 지원
- 고객센터: 1544-5876
- 이메일: support@ncloud.com
- 문서: https://guide.ncloud-docs.com/

### 시스템 관련 문의
- 시스템 로그 확인
- 이슈 추적
- 성능 최적화

---

## ✅ 배포 완료 체크리스트

- [ ] 네이버 클라우드 서버 생성 완료
- [ ] SSH 접속 확인
- [ ] 프로젝트 파일 업로드 완료
- [ ] deploy_naver_cloud.sh 실행 성공
- [ ] .env 파일에 실제 API 키 입력
- [ ] team_emails.json 업로드 완료
- [ ] 수동 테스트 실행 성공
- [ ] Cron 또는 Systemd 설정 완료
- [ ] 첫 자동 실행 확인
- [ ] 이메일 발송 확인
- [ ] 로그 모니터링 설정

**모든 항목을 완료하면 배포 성공입니다! 🎉**

---

**문서 버전**: 1.0
**최종 수정일**: 2026-01-07
**작성자**: Claude Code Assistant
