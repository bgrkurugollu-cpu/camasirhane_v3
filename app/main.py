from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import secrets
from datetime import datetime, timezone
import time
from sqlalchemy import text

from . import models, database
from .utils import get_client_ip
from .exceptions import AppException
from .logger import log_critical
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .modules.auth.router import router as auth_router
from .modules.kullanici.router import router as kullanici_router
from .modules.islem.router import router as islem_router
from .modules.calisan.router import router as calisan_router
from .modules.kiyafet.router import router as kiyafet_router
from .modules.audit.router import router as audit_router
from .modules.edge.router import router as edge_router

app = FastAPI(
    title="Çamaşırhane Otomasyon Sistemi API",
    docs_url=os.getenv("DOCS_URL", None),
    redoc_url=os.getenv("REDOC_URL", None)
)

origins = os.getenv("CORS_ORIGINS", "http://localhost").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; img-src 'self' data:;"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            # Edge gateway uçları makine-makinedir (cihaz JWT imzası + approval ile
            # korunur); CSRF double-submit cookie uygulanmaz (bkz. docs/adr/0009).
            _csrf_exempt = [
                "/api/v1/auth/token", "/api/v1/auth/refresh", "/api/v1/auth/logout",
                "/api/v1/auth/mfa/verify",
                "/api/v1/edge/enroll", "/api/v1/edge/ingest",
            ]
            if request.url.path not in _csrf_exempt:
                csrf_cookie = request.cookies.get("csrf_token")
                csrf_header = request.headers.get("x-csrf-token")
                if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                    return JSONResponse(status_code=403, content={"detail": "CSRF token eksik veya geçersiz"})
        
        response = await call_next(request)
        if "csrf_token" not in request.cookies:
            csrf_token = secrets.token_hex(32)
            response.set_cookie(key="csrf_token", value=csrf_token, httponly=False, samesite="lax", secure=True)
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)

limiter = Limiter(key_func=lambda request: get_client_ip(request))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Pydantic v2, özel validator'lardan gelen hatalarda ctx içine serialize
    # edilemeyen ValueError objesi koyabilir; jsonable_encoder ile güvenli serialize edilir.
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Girdi doğrulama hatası", "details": jsonable_encoder(exc.errors())}}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Yakalanmayan istisnalar → 'critical' kategorili log + alert (bkz. topoloji.md §13).
    # İç hata detayı istemciye sızdırılmaz.
    log_critical(
        "unhandled_exception",
        path=str(request.url.path), method=request.method,
        error_type=type(exc).__name__, error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Beklenmeyen bir sunucu hatası oluştu."}}
    )

_startup_time = time.time()

models.Base.metadata.create_all(bind=database.engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")

@app.get("/api/health")
def health_check():
    now = datetime.now(timezone.utc)
    uptime_seconds = int(time.time() - _startup_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}sa {minutes}dk {seconds}sn"

    db_status = "healthy"
    db_latency_ms = None
    db_error = None
    try:
        db = database.SessionLocal()
        try:
            t0 = time.time()
            db.execute(text("SELECT 1"))
            db_latency_ms = round((time.time() - t0) * 1000, 2)
        finally:
            db.close()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    table_counts = {}
    try:
        db = database.SessionLocal()
        try:
            table_counts = {
                "calisanlar": db.query(models.Calisan).count(),
                "kiyafetler": db.query(models.Kiyafet).count(),
                "kirli_bekleyen": db.query(models.Kirli_Kiyafet).count(),
                "temiz_rafta": db.query(models.Temiz_Kiyafet).count(),
                "teslim_edilmis": db.query(models.Teslim_Edilen).count(),
                "kullanicilar": db.query(models.User).count(),
            }
        finally:
            db.close()
    except Exception:
        pass

    overall = "healthy" if db_status == "healthy" else "unhealthy"

    result = {
        "status": overall,
        "timestamp": now.isoformat(),
        "uptime": uptime_str,
        "uptime_seconds": uptime_seconds,
        "database": {"status": db_status, "latency_ms": db_latency_ms},
        "table_counts": table_counts,
    }
    if db_error: result["database"]["error"] = db_error
    return result

app.include_router(auth_router, prefix="/api/v1")
app.include_router(kullanici_router, prefix="/api/v1")
app.include_router(islem_router, prefix="/api/v1")
app.include_router(calisan_router, prefix="/api/v1")
app.include_router(kiyafet_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(edge_router, prefix="/api/v1")
