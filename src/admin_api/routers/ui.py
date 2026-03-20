"""Server-rendered admin UI routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="src/admin_api/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})

