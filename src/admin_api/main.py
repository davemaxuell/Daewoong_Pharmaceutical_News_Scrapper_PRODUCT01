"""FastAPI app entrypoint for admin backend."""

from __future__ import annotations

from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import SessionLocal
from .routers import auth, email_history, keywords, monitor, recipients, scraper_control, settings, ui
from .services.keyword_sync import ensure_keywords_seeded
from .services.source_sync import ensure_sources_seeded
from .services.team_sync import ensure_team_data_seeded


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        ensure_sources_seeded(db)
        ensure_keywords_seeded(db)
        ensure_team_data_seeded(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Pharma News Admin API", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/admin_api/static"), name="static")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/system/time", tags=["system"])
def system_time():
    now = datetime.now().astimezone()
    return {
        "server_time": now.isoformat(),
        "timezone": str(now.tzinfo),
    }


app.include_router(auth.router)
app.include_router(keywords.router)
app.include_router(recipients.router)
app.include_router(monitor.router)
app.include_router(scraper_control.router)
app.include_router(settings.router)
app.include_router(email_history.router)
app.include_router(ui.router)
