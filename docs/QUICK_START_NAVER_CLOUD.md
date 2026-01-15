# ⚡ Quick Start Guide - Naver Cloud 배포
# 5분 안에 배포하기

## 📝 준비사항

1. ✅ 네이버 클라우드 계정
2. ✅ API Keys (Gemini, Gmail)
3. ✅ SSH 키 (.pem 파일)

---

## 🚀 5단계 배포

### 1️⃣ 서버 생성 (2분)

```
Naver Cloud Console > Server
- OS: Ubuntu 22.04
- 타입: Compact (2 vCPU, 4GB)
- Public IP: 할당
- ACG: SSH(22) 허용
- 인증키: 새로 생성 → .pem 다운로드
```

### 2️⃣ 파일 업로드 (1분)

**Windows PowerShell에서:**

```powershell
# 경로 수정 필요
$KEY = "C:\path\to\your-key.pem"
$IP = "YOUR_SERVER_IP"

scp -i $KEY -r "C:\Users\user\Desktop\제약 뉴스 에이전트\*" ubuntu@${IP}:/home/ubuntu/pharma_news_agent/
```

### 3️⃣ SSH 접속 & 배포 (1분)

```bash
# 접속
ssh -i your-key.pem ubuntu@YOUR_SERVER_IP

# 배포 스크립트 실행
cd pharma_news_agent
chmod +x deploy_naver_cloud.sh
./deploy_naver_cloud.sh
```

### 4️⃣ API 키 설정 (30초)

```bash
nano .env
```

수정할 내용:
```
GEMINI_API_KEY=실제_키_입력
EMAIL_SENDER=실제_이메일@gmail.com
EMAIL_PASSWORD=앱_비밀번호_16자리
```

저장: `Ctrl+X` → `Y` → `Enter`

### 5️⃣ 자동화 설정 (30초)

```bash
chmod +x setup_cron.sh
./setup_cron.sh
# y 입력
```

---

## ✅ 테스트

```bash
# 가상환경 활성화
source venv/bin/activate

# 테스트 실행 (1일치 뉴스)
python multi_source_scraper.py --days 1 -o test.json

# 성공하면:
cat test.json | head -20
```

---

## 📊 모니터링

```bash
# 로그 확인
tail -f logs/cron_$(date +%Y%m%d).log

# Cron 상태
crontab -l

# 파일 확인
ls -lh multi_source_*
```

---

## 🆘 문제 해결

### 이메일 발송 안됨
```bash
# Gmail 앱 비밀번호 재생성
# https://myaccount.google.com/apppasswords
```

### 메모리 부족
```bash
# Swap 추가
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 패키지 설치 실패
```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## 📞 더 자세한 가이드

전체 가이드: [NAVER_CLOUD_DEPLOYMENT_GUIDE.md](./NAVER_CLOUD_DEPLOYMENT_GUIDE.md)

---

**완료! 🎉**

이제 매일 오전 7시마다 자동으로 뉴스가 수집되고 이메일이 발송됩니다.
