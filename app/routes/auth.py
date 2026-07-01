from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {
        "error": None,
        "app_name": settings.APP_NAME,
    })


@router.post("/login")
def login(request: Request, password: str = Form(...)):
    if password == settings.ADMIN_PASSWORD:
        request.session["logged_in"] = True
        return RedirectResponse("/admin", status_code=303)

    return templates.TemplateResponse(request, "login.html", {
        "error": "ContraseÃ±a incorrecta",
        "app_name": settings.APP_NAME,
    })


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


