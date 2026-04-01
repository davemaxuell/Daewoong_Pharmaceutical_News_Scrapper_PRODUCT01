# One-Server Deployment

This project can run on a single Naver Cloud Ubuntu server without Docker.

## What runs on the same server

- PostgreSQL
- FastAPI admin server
- Scraper pipeline
- Optional Nginx reverse proxy

## Recommended layout

- App root: `/home/ubuntu/pharma_news_agent`
- Python venv: `/home/ubuntu/pharma_news_agent/venv`
- Admin API: port `8000`
- Pipeline: `systemd` timer + service
- Database: local PostgreSQL

## 1) Install Python dependencies

```bash
cd /home/ubuntu/pharma_news_agent
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Install PostgreSQL

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
```

Create DB and user:

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE pharma_admin;
CREATE USER pharma_admin_user WITH PASSWORD 'change-this-password';
GRANT ALL PRIVILEGES ON DATABASE pharma_admin TO pharma_admin_user;
\q
```

## 3) Set environment variables

Put these in `config/.env`:

```env
DATABASE_URL=postgresql://pharma_admin_user:change-this-password@localhost:5432/pharma_admin
ADMIN_JWT_SECRET=replace-with-a-long-random-secret
GEMINI_API_KEY=your-key
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

Notes:

- The admin API reads `DATABASE_URL` and `ADMIN_JWT_SECRET`.
- The pipeline and email sender also read from `config/.env`.

## 4) Bootstrap the admin DB

```bash
cd /home/ubuntu/pharma_news_agent
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

## 5) Start the admin API manually once

```bash
cd /home/ubuntu/pharma_news_agent
source venv/bin/activate
set -a
source config/.env
set +a
python -m uvicorn src.admin_api.main:app --host 0.0.0.0 --port 8000
```

Open:

- `http://YOUR_SERVER_IP:8000/health`
- `http://YOUR_SERVER_IP:8000/admin`

## 6) Install systemd services

Pipeline:

```bash
cd /home/ubuntu/pharma_news_agent
chmod +x scripts/linux/setup_systemd.sh
./scripts/linux/setup_systemd.sh
```

Admin API:

```bash
cd /home/ubuntu/pharma_news_agent
chmod +x scripts/linux/setup_admin_systemd.sh
./scripts/linux/setup_admin_systemd.sh
```

## 7) Useful checks

```bash
sudo systemctl status systemd_pharma_news.timer
sudo systemctl status systemd_pharma_news.service
sudo systemctl status systemd_pharma_admin_api.service
```

```bash
tail -f logs/systemd_output.log
tail -f logs/admin_api_output.log
tail -f logs/admin_api_error.log
```

## 8) Optional Nginx reverse proxy

If you want the admin UI behind port 80, keep the FastAPI app on port `8000` and put Nginx in front of it.

Why: the bundled `systemd_pharma_admin_api.service` runs as the non-root `develop` user, so it cannot bind directly to privileged port `80` without extra Linux capability changes.

```bash
sudo apt-get install -y nginx
```

Use the included helper:

```bash
cd /home/ubuntu/pharma_news_agent
chmod +x scripts/linux/setup_admin_nginx.sh
./scripts/linux/setup_admin_nginx.sh YOUR_SERVER_IP 8000
```

This installs Nginx and renders `config/nginx/pharma_admin.conf.template` into `/etc/nginx/sites-available/pharma_admin`.

Example server block:

```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

After that, open:

- `http://YOUR_SERVER_IP/health`
- `http://YOUR_SERVER_IP/admin`

## Docker?

Docker is optional here, not required.

Use Docker only if you want:

- easier reproducible deployment
- stricter process isolation
- container-based ops workflow

For a single small VM, `venv + systemd + PostgreSQL` is simpler and fits this repo well.
