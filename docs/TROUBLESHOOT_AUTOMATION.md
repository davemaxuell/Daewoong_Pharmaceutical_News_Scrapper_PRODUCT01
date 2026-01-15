# 🔧 자동 실행 문제 해결 가이드
# Troubleshooting: System Not Running at 7 AM

## 📋 문제: 매일 오전 7시에 자동 실행이 안됨

---

## 🔍 1단계: 현재 상태 확인

서버에 SSH로 접속 후 다음 명령어를 실행하세요:

### A. Cron 설정 확인

```bash
# Cron 작업 목록 확인
crontab -l

# 예상 출력:
# 0 7 * * * cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py >> /home/ubuntu/pharma_news_agent/logs/cron_$(date +\%Y\%m\%d).log 2>&1

# 만약 "no crontab for ubuntu" 라고 나오면 → Cron이 설정 안됨
```

### B. Systemd 타이머 확인

```bash
# Systemd 타이머 상태 확인
sudo systemctl status systemd_pharma_news.timer

# 타이머 목록 확인
sudo systemctl list-timers | grep pharma

# 만약 "Unit systemd_pharma_news.timer could not be found" → Systemd 설정 안됨
```

### C. 서버 시간대 확인

```bash
# 현재 서버 시간 확인
date

# 시간대 확인
timedatectl

# KST(한국 시간)인지 확인!
# 만약 UTC라면 → 한국시간 오전 7시는 UTC 22시
```

---

## 🛠️ 2단계: 문제 진단 및 해결

### 문제 1: Cron이 설정되지 않음

**증상:**
```bash
crontab -l
# no crontab for ubuntu
```

**해결책:**

```bash
cd /home/ubuntu/pharma_news_agent

# setup_cron.sh 실행
chmod +x setup_cron.sh
./setup_cron.sh

# y 입력하여 Cron 추가

# 확인
crontab -l
```

---

### 문제 2: Cron은 설정되었지만 실행 안됨

**증상:**
```bash
crontab -l  # Cron 작업이 보이지만 실행 안됨
```

**원인:**
- Python 경로 문제
- 권한 문제
- 환경변수 문제

**해결책:**

#### Step 1: 경로 확인

```bash
# Python 경로 확인
ls -la /home/ubuntu/pharma_news_agent/venv/bin/python

# run_pipeline.py 확인
ls -la /home/ubuntu/pharma_news_agent/run_pipeline.py

# .env 파일 확인
ls -la /home/ubuntu/pharma_news_agent/.env
```

#### Step 2: 수동 실행 테스트

```bash
cd /home/ubuntu/pharma_news_agent

# Cron과 똑같은 명령어로 수동 실행
/home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py

# 에러 나오면 → 에러 메시지 확인
# 성공하면 → Cron 설정 문제
```

#### Step 3: Cron 재설정 (절대 경로 사용)

```bash
# 기존 Cron 삭제
crontab -r

# 새로운 Cron 추가
crontab -e

# 다음 내용 추가 (i 키로 입력 모드):
0 7 * * * cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py >> /home/ubuntu/pharma_news_agent/logs/cron_$(date +\%Y\%m\%d).log 2>&1

# 저장: ESC → :wq → Enter
```

---

### 문제 3: 시간대 문제 (UTC vs KST)

**증상:**
```bash
timedatectl
# Time zone: Etc/UTC
```

**해결책:**

```bash
# 한국 시간대로 변경
sudo timedatectl set-timezone Asia/Seoul

# 확인
date
# 출력: 2026년 01월 07일 (화) 오후 04:30:00 KST

# Cron 재시작
sudo service cron restart
```

**또는 Cron 시간 조정:**

```bash
# 만약 서버를 UTC로 유지하고 싶다면
# KST 오전 7시 = UTC 오전 10시 (전날 22시)

crontab -e

# UTC 기준으로 설정:
0 22 * * * cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py >> /home/ubuntu/pharma_news_agent/logs/cron_$(date +\%Y\%m\%d).log 2>&1
```

---

### 문제 4: 로그 디렉토리 권한 문제

**증상:**
```bash
ls -la logs/
# drwxr-xr-x root root  # root 소유
```

**해결책:**

```bash
# logs 디렉토리를 ubuntu 사용자 소유로 변경
sudo chown -R ubuntu:ubuntu /home/ubuntu/pharma_news_agent/logs/

# 권한 확인
ls -la logs/
# drwxr-xr-x ubuntu ubuntu
```

---

### 문제 5: .env 파일 없음

**증상:**
```bash
ls -la .env
# No such file or directory
```

**해결책:**

```bash
# .env 파일 생성
nano .env

# 다음 내용 입력:
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
ENVIRONMENT=production

# 저장: Ctrl+X → Y → Enter

# 권한 설정
chmod 600 .env
```

---

## 🧪 3단계: 테스트

### 즉시 실행 테스트

```bash
# Cron으로 1분 뒤 실행 테스트
crontab -e

# 현재 시간 +1분으로 설정
# 예: 현재 14:30이면
31 14 * * * cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py >> /home/ubuntu/pharma_news_agent/logs/test_$(date +\%Y\%m\%d).log 2>&1

# 저장 후 1분 기다리기

# 로그 확인
tail -f logs/test_$(date +%Y%m%d).log
```

---

## 📊 4단계: 로그 확인

### Cron 실행 로그

```bash
# Cron 실행 여부 확인 (시스템 로그)
sudo grep CRON /var/log/syslog | tail -20

# 출력 예시:
# Jan 7 07:00:01 CRON[1234]: (ubuntu) CMD (cd /home/ubuntu/pharma_news_agent && ...)

# 파이프라인 로그 확인
ls -lht logs/

# 오늘 로그 확인
tail -100 logs/cron_$(date +%Y%m%d).log
```

### 에러 로그 확인

```bash
# 에러만 확인
tail -100 logs/cron_$(date +%Y%m%d).log | grep -i error

# Python 에러 확인
tail -100 logs/cron_$(date +%Y%m%d).log | grep -i traceback
```

---

## ✅ 5단계: 완전 재설정 (모두 실패 시)

모든 방법이 실패하면 완전 재설정:

```bash
cd /home/ubuntu/pharma_news_agent

# 1. 기존 Cron 삭제
crontab -r

# 2. Systemd 제거 (설치했다면)
sudo systemctl stop systemd_pharma_news.timer
sudo systemctl disable systemd_pharma_news.timer
sudo rm /etc/systemd/system/systemd_pharma_news.*

# 3. 시간대 설정
sudo timedatectl set-timezone Asia/Seoul

# 4. 로그 디렉토리 권한
sudo chown -R ubuntu:ubuntu /home/ubuntu/pharma_news_agent/

# 5. .env 확인
cat .env | head -3
# API 키가 있는지 확인

# 6. 수동 테스트
source venv/bin/activate
python run_pipeline.py
# 성공하는지 확인!

# 7. Cron 재설정
./setup_cron.sh
# y 입력

# 8. 확인
crontab -l

# 9. 1분 뒤 테스트
crontab -e
# 현재 시간 +1분으로 설정하여 테스트
```

---

## 🎯 가장 흔한 원인 TOP 5

1. **Cron이 설정 안됨** (50%)
   - 해결: `./setup_cron.sh` 실행

2. **시간대 문제** (UTC vs KST) (20%)
   - 해결: `sudo timedatectl set-timezone Asia/Seoul`

3. **Python 경로 문제** (15%)
   - 해결: 절대 경로 사용

4. **.env 파일 없음** (10%)
   - 해결: `.env` 파일 생성 및 API 키 입력

5. **권한 문제** (5%)
   - 해결: `sudo chown -R ubuntu:ubuntu /home/ubuntu/pharma_news_agent/`

---

## 📞 추가 도움

위의 모든 단계를 시도해도 안되면:

### 디버그 정보 수집

```bash
# 다음 명령어들을 실행하고 결과를 공유하세요:

echo "=== Cron Status ==="
crontab -l

echo "=== Timezone ==="
timedatectl

echo "=== Python Path ==="
ls -la /home/ubuntu/pharma_news_agent/venv/bin/python

echo "=== .env File ==="
ls -la /home/ubuntu/pharma_news_agent/.env

echo "=== Recent Logs ==="
ls -lht /home/ubuntu/pharma_news_agent/logs/ | head -10

echo "=== Cron Log (System) ==="
sudo grep CRON /var/log/syslog | tail -10

echo "=== Manual Test ==="
cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python --version
```

---

## 🚀 빠른 해결 명령어 모음

```bash
# 한 번에 실행할 수 있는 명령어들

# 시간대 설정 + Cron 재설정
sudo timedatectl set-timezone Asia/Seoul && \
cd /home/ubuntu/pharma_news_agent && \
sudo chown -R ubuntu:ubuntu /home/ubuntu/pharma_news_agent/ && \
chmod +x setup_cron.sh && \
./setup_cron.sh

# Cron 즉시 테스트 (현재 시간 +2분)
crontab -e
# 다음 줄 추가 (시간은 현재 +2분으로):
# 32 14 * * * cd /home/ubuntu/pharma_news_agent && /home/ubuntu/pharma_news_agent/venv/bin/python /home/ubuntu/pharma_news_agent/run_pipeline.py >> /home/ubuntu/pharma_news_agent/logs/test.log 2>&1

# 로그 실시간 확인
tail -f logs/test.log
```

---

**이 가이드를 따라하면 자동 실행이 작동할 것입니다!** 🎉

문제가 지속되면 위의 디버그 정보를 수집해서 공유해주세요.
