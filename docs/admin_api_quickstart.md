# Admin API Quickstart

## 1) Install dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2) Set environment variables
```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/pharma_admin"
$env:ADMIN_JWT_SECRET="replace-with-a-long-random-secret"
```

## 3) Bootstrap schema and seed data
```powershell
.\.venv\Scripts\python.exe scripts\db\bootstrap_admin_db.py
```

## 4) Create initial admin user
```powershell
.\.venv\Scripts\python.exe scripts\db\create_admin_user.py `
  --db-url $env:DATABASE_URL `
  --email admin@example.com `
  --password "ChangeMe123!" `
  --full-name "Admin"
```

## 5) Run API server
```powershell
.\.venv\Scripts\python.exe -m uvicorn src.admin_api.main:app --reload --host 0.0.0.0 --port 8000
```

## 6) Open admin UI
Open: `http://localhost:8000/admin`

Sign in with your admin user credentials.

## 7) Optional API login test
```powershell
curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"admin@example.com\",\"password\":\"ChangeMe123!\"}"
```

Use the returned bearer token in `Authorization: Bearer <token>`.

## Available endpoints
- `GET /health`
- `POST /auth/login`
- `GET /auth/me`
- `GET/POST/PUT/DELETE /keywords`
- `GET /recipients/teams`
- `GET/POST/PUT/DELETE /recipients`
