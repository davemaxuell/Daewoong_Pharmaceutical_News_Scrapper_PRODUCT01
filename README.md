# 대웅제약 뉴스 스크래퍼 및 관리자 시스템

대웅제약 관련 뉴스와 규제 업데이트를 자동 수집하고, AI 요약과 팀별 메일 발송까지 수행하는 프로젝트입니다.  
관리자 UI를 통해 키워드, 수신자, 팀 라우팅, 소스 설정, 실행 이력, 이메일 이력을 함께 관리할 수 있습니다.

## 개요

이 프로젝트는 아래 흐름으로 동작합니다.

1. 여러 국내외 뉴스/규제 소스에서 기사를 수집합니다.
2. Gemini 기반 AI 분석으로 요약, 핵심 포인트, 영향도를 생성합니다.
3. 키워드와 분류 결과를 기준으로 팀별 메일을 발송합니다.
4. 관리자 UI에서 운영 설정과 이력을 확인하고 수정합니다.

## 주요 기능

- 다중 소스 뉴스 수집
- 규제/가이드라인 변경 모니터링
- AI 요약 및 핵심 포인트 생성
- 팀별 키워드 및 수신자 라우팅
- 관리자 UI 기반 설정 관리
- 이메일 발송 이력 및 실행 로그 조회
- PostgreSQL 기반 운영 데이터 관리

## 현재 관리자 UI와 DB가 연결되는 항목

다음 항목은 관리자 UI에서 수정하면 실제 런타임 동작에도 반영됩니다.

- 키워드 관리
  - 스크래퍼 분류는 활성 키워드를 DB에서 읽어 사용합니다.
- 수신자/팀 관리
  - 이메일 라우팅은 팀, 팀-카테고리, 수신자 매핑을 DB에서 읽어 사용합니다.
- 소스 설정
  - 소스 활성화 여부
  - 소스별 `timeout_seconds`
  - 소스별 `max_items`
- 일반 설정
  - `max_total_articles`
- 스케줄 설정
  - DB의 스케줄 활성화 여부는 자동 실행 시 파이프라인이 확인합니다.

## 운영 정책

- 토요일, 일요일에는 메일을 발송하지 않습니다.
- 월요일 실행 시 최근 3일치를 조회하여 주말 수집분을 함께 반영합니다.
- 관리자 UI에서 전체 파이프라인을 수동 실행하면, DB 스케줄이 꺼져 있어도 강제로 실행할 수 있습니다.

주의:

- 관리자 UI에서 저장하는 `실행 시간`은 DB에 기록됩니다.
- 실제 OS 스케줄러(`systemd` 또는 `cron`)의 실행 시각까지 자동으로 바꾸지는 않습니다.
- 실행 시간까지 바꾸려면 서버의 `systemd`/`cron` 설정도 함께 수정해야 합니다.

## 디렉터리 구조

```text
.
├── README.md
├── config/
├── data/
├── docs/
├── scrapers/
├── scripts/
├── src/
│   ├── admin_api/
│   ├── ai_summarizer_gemini.py
│   ├── email_sender.py
│   ├── keywords.py
│   ├── monitor_pipeline.py
│   ├── multi_source_scraper.py
│   ├── run_pipeline.py
│   └── team_definitions.py
├── systemd_pharma_admin_api.service
├── systemd_pharma_news.service
└── systemd_pharma_news.timer
```

## 요구 사항

- Python 3.11 이상 권장
- PostgreSQL
- Gemini API Key
- 메일 발송용 SMTP 계정

## 빠른 시작

### 1. 저장소 준비

```bash
git clone https://github.com/davemaxuell/Daewoong_Pharmaceutical_News_Scrapper_PRODUCT01.git
cd Daewoong_Pharmaceutical_News_Scrapper_PRODUCT01
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows라면:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

프로젝트는 `PROJECT_ROOT/.env` 또는 `PROJECT_ROOT/config/.env`를 자동으로 읽습니다.

예시:

```env
DATABASE_URL=postgresql://pharma_admin_user:change-this-password@localhost:5432/pharma_admin
ADMIN_JWT_SECRET=replace-with-a-long-random-secret

GEMINI_API_KEY=your-gemini-key

SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

OPENFDA_API_KEY=your-openfda-key
```

### 3. 관리자 DB 초기화

```bash
source venv/bin/activate
set -a
source config/.env
set +a
python scripts/db/bootstrap_admin_db.py
python scripts/db/create_admin_user.py \
  --db-url "$DATABASE_URL" \
  --email admin@example.com \
  --password 'ChangeMe123!' \
  --full-name 'Admin'
```

### 4. 관리자 UI 실행

```bash
source venv/bin/activate
set -a
source config/.env
set +a
python -m uvicorn src.admin_api.main:app --host 0.0.0.0 --port 8000
```

접속 주소:

- `http://localhost:8000/health`
- `http://localhost:8000/admin`

### 5. 전체 파이프라인 수동 실행

```bash
source venv/bin/activate
python src/run_pipeline.py
```

## 자주 쓰는 명령어

### 뉴스만 수집

```bash
python src/multi_source_scraper.py --days 1 -o data/news/manual_news.json
```

### AI 요약만 실행

```bash
python src/ai_summarizer_gemini.py -i data/news/manual_news.json -o data/news/manual_summary.json
```

### 규제 모니터링만 실행

```bash
python src/monitor_pipeline.py
```

### 소스 상태 진단

```bash
python scripts/diagnose_latest_sources.py --days 2
```

### 관리자 DB 시드 다시 반영

```bash
python scripts/db/bootstrap_admin_db.py
```

## 출력 파일 위치

- 뉴스 수집 결과: `data/news/`
- 모니터링 결과: `data/monitors/`
- 진단 결과: `data/diagnostics/`
- 로그: `logs/`

## 자동 실행

### systemd 사용 시

```bash
chmod +x scripts/linux/setup_systemd.sh
./scripts/linux/setup_systemd.sh
```

### cron 사용 시

```bash
chmod +x scripts/linux/setup_cron.sh
./scripts/linux/setup_cron.sh
```

기본 정책은 평일 오전 실행입니다.

## 관련 문서

- `docs/ONE_SERVER_DEPLOYMENT.md`
- `docs/admin_api_quickstart.md`
- `docs/QUICK_START_NAVER_CLOUD.md`
- `docs/NAVER_CLOUD_DEPLOYMENT_GUIDE.md`
- `docs/PIPELINE_IMPROVEMENT_GUIDE.md`

## 참고 사항

- 관리자 UI의 키워드/수신자/팀/소스 설정은 PostgreSQL을 기준으로 운영됩니다.
- 분류 로직은 런타임에 DB의 활성 키워드를 우선 사용합니다.
- 이메일 라우팅은 DB의 팀/수신자 매핑을 우선 사용합니다.
- OS 스케줄러 시간 변경 자동화는 아직 별도 배포 단계가 필요합니다.
