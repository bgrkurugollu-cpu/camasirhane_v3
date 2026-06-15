# LaundroStar — Backend Mimarisi ve Kod Organizasyonu

> Bu doküman backend'in nasıl organize edildiğini ve nasıl yazıldığını tanımlar. Agent yeni bir feature eklerken: nereye dosya koyacağını, hangi pattern'i kullanacağını, servisini nasıl yapılandıracağını, hata fırlatma disiplinini, audit hook'larının nasıl çalıştığını — hepsini tek yerden öğrenir.

---

## 1. Framework ve Runtime

| Bileşen | Versiyon | Not |
|---------|----------|-----|
| Python | 3.11 | Pinned; `.python-version` + `Dockerfile` ile zorlanır |
| FastAPI | 0.111+ | Starlette tabanlı ASGI |
| Uvicorn | 0.29+ | ASGI server; `--proxy-headers` aktif |
| SQLAlchemy | 2.0+ | Sync (thread pool model) |
| Alembic | 1.13+ | Migration yönetimi |
| Pydantic | v2 | Request/response validation |
| passlib[bcrypt] | 1.7+ | bcrypt cost 12 |
| python-jose[cryptography] | — | JWT RS256 |
| structlog | 24+ | Structured JSON logging |
| slowapi | 0.1.9+ | Rate limiting |
| pytest | 8+ | Test framework |
| pytest-cov | — | Coverage raporu |

---

## 2. Klasör Yapısı — `apps/api/`

```
apps/api/
├── main.py                          # FastAPI app factory + middleware kayıtları
├── config.py                        # Pydantic Settings (env validation)
│
├── bootstrap/
│   ├── migrations.py                # Alembic upgrade head çalıştırır
│   └── seed.py                      # Admin user + dev seed (env flag ile)
│
├── common/
│   ├── dependencies.py              # get_db, get_current_user, require_admin
│   ├── security_headers.py          # Middleware: CSP, X-Frame-Options vs.
│   ├── rate_limiter.py              # slowapi Limiter instance
│   ├── audit.py                     # write_audit_log() helper
│   ├── ip_utils.py                  # get_client_ip(), hash_ip()
│   ├── exceptions.py                # AppException hiyerarşisi
│   └── response.py                  # success_response(), error_response() helper
│
├── modules/
│   ├── auth/
│   │   ├── router.py                # /api/v1/auth/*
│   │   ├── service.py               # login, refresh, logout iş mantığı
│   │   ├── schemas.py               # LoginRequest, TokenResponse
│   │   └── tests/
│   │       └── test_auth.py
│   │
│   ├── users/
│   │   ├── router.py                # /api/v1/users/*
│   │   ├── service.py               # CRUD, photo upload iş mantığı
│   │   ├── repository.py            # DB erişim katmanı
│   │   ├── schemas.py               # UserResponse, UserCreate, UserProfileUpdate
│   │   └── tests/
│   │       └── test_users.py
│   │
│   ├── calisanlar/
│   │   ├── router.py                # /api/v1/calisanlar/*
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── tests/
│   │
│   ├── kiyafetler/
│   │   ├── router.py                # /api/v1/kiyafetler/*
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── tests/
│   │
│   ├── islem/
│   │   ├── router.py                # /api/v1/islem/*
│   │   ├── service.py               # kirli giris, onayla, teslim iş mantığı
│   │   ├── repository.py
│   │   ├── shelf_service.py         # Raf atama algoritması (izole)
│   │   ├── schemas.py
│   │   └── tests/
│   │       └── test_islem.py
│   │
│   ├── stats/
│   │   ├── router.py                # /api/v1/stats/*
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── tests/
│   │
│   └── audit/
│       ├── router.py                # /api/v1/audit-logs
│       ├── repository.py
│       ├── schemas.py
│       └── tests/
│
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── calisan.py
│   ├── kiyafet.py
│   ├── laundry.py                   # KirliKiyafet, TemizKiyafet, TeslimEdilen
│   └── audit_log.py
│
├── database.py                      # Engine, SessionLocal, get_db
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py
│
├── alembic.ini
│
├── static/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── avatars/
│
├── tests/
│   ├── conftest.py                  # pytest fixtures (test DB, test client)
│   └── integration/
│       └── test_laundry_flow.py     # Uçtan uca akış testi
│
├── Dockerfile
├── .env.example
├── requirements.txt
└── pytest.ini
```

---

## 3. Modül İskeleti Konvansiyonu

Her modül aynı yapıyı takip eder:

| Dosya | Zorunlu | Amaç |
|-------|---------|------|
| `router.py` | Evet | FastAPI APIRouter; yalnızca HTTP endpoint tanımları |
| `service.py` | Evet | İş mantığı; transaction, validation, orchestration |
| `repository.py` | Evet (DB'ye dokunan modüller) | SQLAlchemy sorguları; service'e db nesnesi döner |
| `schemas.py` | Evet | Pydantic request/response modelleri |
| `tests/` | Evet | Modüle ait unit testler |

**Kural:** `router.py` içinde business logic **yoktur**; yalnızca:
1. HTTP decorator (`@router.post(...)`)
2. Dependency injection parametreleri
3. `service.function(...)` çağrısı
4. Response şemalandırma

---

## 4. Router Pattern

```python
# modules/islem/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from common.dependencies import get_db, get_current_user
from models.user import User
from . import service, schemas

router = APIRouter(prefix="/api/v1/islem", tags=["islem"])

@router.post("/kirli-giris", response_model=schemas.KirliGirisResponse, status_code=201)
def kirli_giris(
    req: schemas.KirliGirisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return service.kirli_giris(db=db, req=req, current_user=current_user)
```

---

## 5. Service Pattern

```python
# modules/islem/service.py
from sqlalchemy.orm import Session
from common.audit import write_audit_log
from common.exceptions import AppException
from . import repository, schemas
from .shelf_service import assign_shelf

def kirli_giris(db: Session, req: schemas.KirliGirisRequest, current_user) -> dict:
    kiyafet = repository.get_kiyafet_by_rfid(db, req.rfid_tag)
    if not kiyafet:
        raise AppException("ISLEM_RFID_NOT_REGISTERED", status_code=404)

    yeni = repository.create_kirli(db, rfid_tag=req.rfid_tag,
                                    sicil=kiyafet.sicil_numarasi,
                                    user_id=current_user.id)
    write_audit_log(db, action="KIRLI_GIRIS",
                    username=current_user.username,
                    detail=f"RFID:{req.rfid_tag} Sicil:{kiyafet.sicil_numarasi}",
                    user_id=current_user.id)
    return {"id": yeni.id, "rfid_tag": yeni.rfid_tag, "sicil_numarasi": yeni.sicil_numarasi}
```

**Service kuralları:**
- `Request` / `Response` HTTP objesi service katmanına **girmez**.
- Her iş kuralı ihlali `AppException` ile fırlatılır.
- Audit log her state-changing fonksiyonun sonunda yazılır.
- Transaction yönetimi service katmanındadır; repository commit yapmaz.

---

## 6. Repository Pattern

```python
# modules/islem/repository.py
from sqlalchemy.orm import Session
from models.laundry import KirliKiyafet

def get_kirli_by_id(db: Session, id: int) -> KirliKiyafet | None:
    return db.query(KirliKiyafet).filter(KirliKiyafet.id == id).first()

def create_kirli(db: Session, rfid_tag: str, sicil: str, user_id: str) -> KirliKiyafet:
    kayit = KirliKiyafet(rfid_tag=rfid_tag, sicil_numarasi=sicil, created_by_user_id=user_id)
    db.add(kayit)
    db.flush()   # id'yi al; commit service'te yapılır
    return kayit
```

**Repository kuralları:**
- Yalnızca SQLAlchemy query'leri.
- `db.commit()` çağrılmaz; `db.flush()` ile id alınabilir.
- İş kuralı yoktur.

---

## 7. Exception Hiyerarşisi

```python
# common/exceptions.py
class AppException(Exception):
    def __init__(self, code: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.status_code = status_code
        self.details = details

# FastAPI exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": ERROR_MESSAGES.get(exc.code, exc.code)}}
    )
```

Tüm hata mesajları `ERROR_MESSAGES` dict'inden alınır; controller veya service içinde doğrudan string yazılmaz.

---

## 8. Audit Log Helper

```python
# common/audit.py
import hashlib
from sqlalchemy.orm import Session
from models.audit_log import AuditLog

def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()

def write_audit_log(
    db: Session,
    action: str,
    username: str | None = None,
    detail: str | None = None,
    ip: str | None = None,          # plaintext; hash'lenerek kaydedilir
    user_id: str | None = None,
    status: str = "success"
):
    log = AuditLog(
        action=action,
        username=username,
        detail=detail,
        ip_hash=hash_ip(ip) if ip else None,
        status=status,
        created_by_user_id=user_id
    )
    db.add(log)
    # commit service katmanında
```

---

## 9. Dependency Injection

```python
# common/dependencies.py
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from modules.auth.service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = decode_access_token(token, db)
    if not user or not user.is_active:
        raise AppException("AUTH_TOKEN_INVALID", status_code=401)
    return user

def require_admin(current_user = Depends(get_current_user)):
    if current_user.role != "admin":
        raise AppException("AUTH_FORBIDDEN", status_code=403)
    return current_user
```

---

## 10. Loglama

```python
# main.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
```

**Kural:**
- Tüm log çıktısı JSON formatında (`structlog`).
- Her log kaydında: `timestamp`, `level`, `service`, `message`.
- PII alanları (email, sicil, IP) log'a düz metin olarak **yazılmaz**.
- `logger.info(...)`, `logger.warning(...)`, `logger.error(...)` kullanılır; `print()` yasaktır.

---

## 11. Config (Pydantic Settings)

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    admin_username: str = "admin"
    admin_password_hash: str
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    upload_dir: str = "app/static/avatars"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

Uygulama başlarken env validation fail olursa `ValidationError` ile çöker; bu beklenen davranıştır.

---

## 12. Main App Factory

```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from common.security_headers import SecurityHeadersMiddleware
from bootstrap.migrations import run_migrations
from bootstrap.seed import ensure_admin

from modules.auth.router import router as auth_router
from modules.users.router import router as users_router
from modules.calisanlar.router import router as calisanlar_router
from modules.kiyafetler.router import router as kiyafetler_router
from modules.islem.router import router as islem_router
from modules.stats.router import router as stats_router
from modules.audit.router import router as audit_router

def create_app() -> FastAPI:
    run_migrations()
    ensure_admin()

    app = FastAPI(title="LaundroStar API", docs_url=None, redoc_url=None)  # Prod'da docs kapalı

    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(calisanlar_router)
    app.include_router(kiyafetler_router)
    app.include_router(islem_router)
    app.include_router(stats_router)
    app.include_router(audit_router)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    return app

app = create_app()
```

---

## 13. Shelf Service (Raf Atama)

Raf atama algoritması izole bir servis olarak yaşar; islem.service.py tarafından çağrılır.

```python
# modules/islem/shelf_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.laundry import TemizKiyafet

RACK_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
RACK_FLOORS = 7
RACK_COMPARTMENTS = 5

def get_capacity(floor: int) -> int:
    return 1 if floor == 7 else 3

def assign_shelf(db: Session, cinsiyet: str | None = None) -> str | None:
    """
    Uygun ilk boş raf bölmesini döndürür.
    Uygun bölme yoksa None döner → service 409 SHELF_FULL fırlatır.
    """
    occupancy = dict(
        db.query(TemizKiyafet.raf_id, func.count(TemizKiyafet.id))
          .filter(TemizKiyafet.raf_id.isnot(None))
          .group_by(TemizKiyafet.raf_id)
          .all()
    )

    letters = ['E'] if cinsiyet == 'K' else [l for l in RACK_LETTERS if l != 'E']

    for letter in letters:
        for floor in range(1, RACK_FLOORS + 1):
            cap = get_capacity(floor)
            for comp in range(1, RACK_COMPARTMENTS + 1):
                raf_id = f"{letter}{floor}{comp}"
                if occupancy.get(raf_id, 0) < cap:
                    return raf_id
    return None
```
