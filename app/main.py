from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.customers import router as customers_router

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(customers_router)


@app.get("/")
def home():
    return {"ok": True, "app": settings.APP_NAME}


@app.get("/health")
def health():
    return {"status": "ok"}


