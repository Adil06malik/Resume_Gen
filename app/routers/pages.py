from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.routers.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent.parent / "templates")
router = APIRouter()


def _has_token(request: Request) -> bool:
    return bool(request.cookies.get("access_token"))


async def _render(request: Request, template: str, **ctx):
    if not _has_token(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, template, ctx)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if _has_token(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _has_token(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    user = None
    try:
        from fastapi import Depends
    except Exception:
        pass
    return templates.TemplateResponse(request, "dashboard.html", {"token": token})


@router.get("/resumes", response_class=HTMLResponse)
@router.get("/jobs", response_class=HTMLResponse)
@router.get("/applications", response_class=HTMLResponse)
@router.get("/applications/{app_id}", response_class=HTMLResponse)
async def old_pages(request: Request, app_id: int = None):
    return RedirectResponse("/dashboard", status_code=302)
