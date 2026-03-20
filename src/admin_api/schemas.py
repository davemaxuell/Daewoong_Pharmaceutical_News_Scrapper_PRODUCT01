"""Pydantic schemas for API IO."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=6)


class MeResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    roles: list[str]
    is_active: bool


class KeywordCreateRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    category_names: list[str] = Field(default_factory=list)
    language_code: str = Field(default="ko", max_length=16)
    is_active: bool = True


class KeywordUpdateRequest(BaseModel):
    keyword: str | None = Field(default=None, min_length=1, max_length=200)
    category_names: list[str] | None = None
    language_code: str | None = Field(default=None, max_length=16)
    is_active: bool | None = None


class KeywordResponse(BaseModel):
    id: UUID
    keyword: str
    normalized_keyword: str
    language_code: str | None
    is_active: bool
    categories: list[str]
    updated_at: datetime


class TeamResponse(BaseModel):
    id: UUID
    name: str


class RecipientCreateRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    team_names: list[str] = Field(default_factory=list)
    is_active: bool = True
    receives_test_emails: bool = False


class RecipientUpdateRequest(BaseModel):
    full_name: str | None = None
    team_names: list[str] | None = None
    is_active: bool | None = None
    receives_test_emails: bool | None = None


class RecipientResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    receives_test_emails: bool
    team_names: list[str]
    updated_at: datetime


class JobResponse(BaseModel):
    id: UUID
    job_type: str
    trigger_type: str
    status: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class JobSourceRunResponse(BaseModel):
    id: UUID
    source_name: str
    status: str
    article_count: int
    error_count: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class AppLogResponse(BaseModel):
    id: int
    level: str
    message: str
    source_name: str | None
    job_id: UUID | None
    created_at: datetime


class ScraperRunRequest(BaseModel):
    source_codes: list[str] = Field(default_factory=list)


class ScraperActionResponse(BaseModel):
    ok: bool
    message: str
    job_id: UUID | None = None


class SourceSettingResponse(BaseModel):
    id: UUID
    code: str
    display_name: str
    scraper_module: str
    is_enabled: bool
    timeout_seconds: int
    max_items: int


class SourceSettingUpdateRequest(BaseModel):
    is_enabled: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    max_items: int | None = Field(default=None, ge=1)


class GeneralSettingsResponse(BaseModel):
    scrape_frequency_minutes: int
    max_total_articles: int


class GeneralSettingsUpdateRequest(BaseModel):
    scrape_frequency_minutes: int = Field(ge=1, le=1440)
    max_total_articles: int = Field(ge=1, le=100000)


class ScheduleResponse(BaseModel):
    id: UUID
    name: str
    cron_expr: str
    timezone: str
    is_enabled: bool


class ScheduleUpdateRequest(BaseModel):
    cron_expr: str
    timezone: str = "Asia/Seoul"
    is_enabled: bool = True


class SettingsOverviewResponse(BaseModel):
    sources: list[SourceSettingResponse]
    general: GeneralSettingsResponse
    schedule: ScheduleResponse


class EmailCampaignResponse(BaseModel):
    id: UUID
    subject: str
    article_count: int
    status: str
    team_names: list[str] = Field(default_factory=list)
    created_at: datetime
    sent_at: datetime | None


class EmailDeliveryResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    team_names: list[str] = Field(default_factory=list)
    delivery_type: str
    status: str
    error_message: str | None
    sent_at: datetime | None


class EmailCampaignDetailResponse(BaseModel):
    id: UUID
    subject: str
    body_html: str | None
    body_text: str | None
    article_count: int
    status: str
    team_names: list[str] = Field(default_factory=list)
    created_at: datetime
    sent_at: datetime | None
    deliveries: list[EmailDeliveryResponse]
