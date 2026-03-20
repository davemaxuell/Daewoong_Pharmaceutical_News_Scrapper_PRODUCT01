-- Admin Website v1 PostgreSQL schema
-- Target: keyword/recipient management, scraper operations, logs, email history, settings, audit

BEGIN;

-- Optional extension for UUIDs
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Auth & access control
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE CHECK (name IN ('admin', 'viewer')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

-- 2) Keyword domain
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    normalized_keyword TEXT NOT NULL,
    language_code TEXT DEFAULT 'ko',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (normalized_keyword, language_code)
);

CREATE TABLE IF NOT EXISTS keyword_category_map (
    keyword_id UUID NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (keyword_id, category_id)
);

-- 3) Team & recipients
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_category_map (
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, category_id)
);

CREATE TABLE IF NOT EXISTS recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    receives_test_emails BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (position('@' IN email) > 1)
);

CREATE TABLE IF NOT EXISTS recipient_team_map (
    recipient_id UUID NOT NULL REFERENCES recipients(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (recipient_id, team_id)
);

-- 4) Sources, settings, schedules
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    scraper_module TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    timeout_seconds INTEGER NOT NULL DEFAULT 120 CHECK (timeout_seconds > 0),
    max_items INTEGER NOT NULL DEFAULT 200 CHECK (max_items > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    cron_expr TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Seoul',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5) Scraper execution tracking
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL CHECK (job_type IN ('scrape', 'email_send', 'test_email')),
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'scheduled', 'retry', 'system')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'success', 'failed', 'cancelled')),
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN started_at IS NOT NULL AND finished_at IS NOT NULL
            THEN (EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000)::INTEGER
            ELSE NULL
        END
    ) STORED,
    summary JSONB NOT NULL DEFAULT '{}'::JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_source_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'success', 'failed', 'skipped')),
    article_count INTEGER NOT NULL DEFAULT 0 CHECK (article_count >= 0),
    error_count INTEGER NOT NULL DEFAULT 0 CHECK (error_count >= 0),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN started_at IS NOT NULL AND finished_at IS NOT NULL
            THEN (EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000)::INTEGER
            ELSE NULL
        END
    ) STORED,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);

-- 6) Application/system logs
CREATE TABLE IF NOT EXISTS app_logs (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    context JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7) Email preview/send history
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    body_html TEXT,
    body_text TEXT,
    article_count INTEGER NOT NULL DEFAULT 0 CHECK (article_count >= 0),
    status TEXT NOT NULL CHECK (status IN ('draft', 'sending', 'sent', 'failed', 'cancelled')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS email_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
    recipient_id UUID REFERENCES recipients(id) ON DELETE SET NULL,
    email TEXT NOT NULL,
    delivery_type TEXT NOT NULL CHECK (delivery_type IN ('production', 'test')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'failed', 'bounced')),
    provider_message_id TEXT,
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8) Audit trail
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    before_json JSONB,
    after_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id TEXT,
    ip_address INET
);

-- Indexes for expected queries
CREATE INDEX IF NOT EXISTS idx_keywords_normalized ON keywords(normalized_keyword);
CREATE INDEX IF NOT EXISTS idx_recipients_active ON recipients(is_active);
CREATE INDEX IF NOT EXISTS idx_recipient_team_map_team ON recipient_team_map(team_id);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON sources(is_enabled);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_type_created ON jobs(job_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_source_runs_job_id ON job_source_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_job_source_runs_source_status ON job_source_runs(source_id, status);
CREATE INDEX IF NOT EXISTS idx_app_logs_created ON app_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_logs_level_created ON app_logs(level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_logs_source_created ON app_logs(source_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_campaigns_status_created ON email_campaigns(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_campaign ON email_deliveries(campaign_id);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_status_sent ON email_deliveries(status, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_created ON audit_events(actor_user_id, created_at DESC);

-- Seed base roles
INSERT INTO roles (name, description)
VALUES
    ('admin', 'Full access to admin panel and configuration'),
    ('viewer', 'Read-only access to runs/logs and dashboards')
ON CONFLICT (name) DO NOTHING;

COMMIT;
