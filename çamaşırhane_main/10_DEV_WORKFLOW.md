# LaundroStar — Geliştirme İş Akışı

> Bu doküman günlük geliştirme disiplinini tanımlar: repository organizasyonu, branch adlandırma, commit standardı, PR akışı, local ortam kurulumu, CI/CD pipeline ve Architecture Decision Records (ADR'lar).

---

## 1. Repository Yapısı

```
camasirhane_v4/
│
├── apps/
│   └── api/                    # FastAPI backend
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── bootstrap/
│       ├── common/
│       ├── modules/
│       ├── models/
│       ├── alembic/
│       ├── static/             # Frontend: HTML, JS, CSS
│       ├── tests/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── alembic.ini
│       └── pytest.ini
│
├── nginx/
│   ├── nginx.conf
│   └── certs/                  # TLS sertifikaları (.gitignore'da)
│
├── docs/                       # Bu dokümantasyon seti
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── ...
│   └── adr/                    # Architecture Decision Records
│       ├── ADR-001-frontend-stack.md
│       └── ADR-002-jwt-rs256.md
│
├── scripts/
│   └── generate-jwt-keys.sh    # RS256 anahtar çifti üretimi
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 2. Git Workflow

### 2.1 Branching Model

**Trunk-based development.** Tek uzun ömürlü branch: `main`. Feature/fix → kısa ömürlü branch (max 3 gün) → PR → squash merge → main.

### 2.2 Branch Naming

```
feat/jwt-httponly-cookie
feat/modular-router-structure
fix/shelf-female-rack-bug
fix/init-mock-data-security
chore/upgrade-fastapi-0111
refactor/split-main-into-modules
docs/update-api-contracts
test/add-auth-integration-tests
ci/add-pip-audit-step
```

### 2.3 Commit Standardı (Conventional Commits)

```
feat: add JWT RS256 + httpOnly cookie auth
fix: remove unauthenticated init_mock_data endpoint
refactor: split main.py into router/service/repository layers
test: add lockout mechanism integration tests
chore: upgrade sqlalchemy to 2.0
ci: add pip-audit security scanning
docs: update API contracts with v1 prefix
```

Format: `<type>: <description>` — Türkçe veya İngilizce, tutarlı kalmak koşuluyla.

### 2.4 PR Kuralları

- PR açılmadan önce: `pytest` yeşil, lint yeşil.
- PR açıklamasında: "Bu PR hangi dokümandaki kuralı uygular?" sorusu yanıtlanır.
- Squash merge — commit geçmişi temiz kalır.
- `main`'e doğrudan push: **yasak**.

---

## 3. Ortam Değişkenleri

`.env.example` dosyası tüm key'leri içerir; `.env` dosyası `.gitignore`'da ve gerçek değerleri taşır.

```bash
# .env.example

# Database
DATABASE_URL=postgresql://camasirhane:changeme@db:5432/camasirhane_db
POSTGRES_USER=camasirhane
POSTGRES_PASSWORD=changeme
POSTGRES_DB=camasirhane_db

# JWT (RS256)
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CSRF / Session
SECRET_KEY=changeme-at-least-32-chars

# Admin seed
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...    # bcrypt ile önceden hash edilmiş

# App
TZ=Europe/Istanbul
DEBUG=false

# Auth
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15
```

**JWT anahtarı üretimi:**
```bash
# scripts/generate-jwt-keys.sh
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

---

## 4. Local Geliştirme Ortamı

### 4.1 İlk Kurulum

```bash
# Repo klonlama ve env hazırlama
cp .env.example .env
# .env içindeki SECRET_KEY, JWT key'leri ve ADMIN_PASSWORD_HASH düzenle

# JWT anahtarları üret
bash scripts/generate-jwt-keys.sh

# Docker servisleri başlat
docker compose up -d db      # Sadece PostgreSQL

# Python ortamı
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt

# Migration çalıştır
cd apps/api
alembic upgrade head

# Uygulamayı başlat
uvicorn main:app --reload --port 8086
```

### 4.2 Docker Compose ile Tam Ortam

```bash
docker compose up --build

# Servisler:
# - db: PostgreSQL 16 (port 5432)
# - web: FastAPI (port 8086; iç ağ)
# - nginx: Nginx (port 80 → 443)
```

### 4.3 Test Çalıştırma

```bash
# Hızlı lokal çalışma (SQLite fallback — env vermeden):
DATABASE_URL=sqlite:///./test.db TEST_DATABASE_URL=sqlite:///./test.db \
  pytest --cov=app --cov-report=term-missing

# CI ile aynı: gerçek PostgreSQL'e karşı (PG'ye özgü davranış sadakati)
docker run -d --name ls_pg -e POSTGRES_USER=camasirhane -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=camasirhane_test -p 5432:5432 postgres:16-alpine
export DATABASE_URL=postgresql://camasirhane:testpass@localhost:5432/camasirhane_test
export TEST_DATABASE_URL="$DATABASE_URL"
pytest
```

> CI (`.github/workflows/ci.yml`) testleri **her zaman** PostgreSQL servis container'ına
> karşı koşar; SQLite yalnızca lokal hız içindir. Coverage eşiği `pytest.ini`
> (`--cov-fail-under=80`) ile zorlanır.

---

## 5. Dockerfile Kuralları

```dockerfile
# apps/api/Dockerfile — Multi-stage build

# Stage 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim AS production
WORKDIR /code

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Sadece runtime ihtiyaçları kopyala
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY ./app /code/app
COPY alembic.ini /code/alembic.ini
COPY alembic/ /code/alembic/

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8086/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8086", "--proxy-headers"]
```

**.dockerignore:**
```
.git
.env
.venv
__pycache__
*.pyc
*.pyo
.pytest_cache
tests/
*.md
nginx/certs/
```

**Docker kuralları (vibecoding standardı):**
- [ ] Multi-stage build ✓
- [ ] Non-root user (`appuser`) ✓
- [ ] Pinned base image (`python:3.11-slim`) ✓
- [ ] `.dockerignore` mevcut ✓
- [ ] Secret'lar image içinde değil ✓
- [ ] Healthcheck tanımlı ✓

---

## 6. CI/CD Pipeline

```yaml
# .github/workflows/pr-check.yml
name: PR Check
on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r apps/api/requirements.txt
      - run: cd apps/api && ruff check app/
      - run: cd apps/api && mypy app/ --ignore-missing-imports
      - run: cd apps/api && pytest --cov=app --cov-fail-under=80
      - run: pip-audit --requirement apps/api/requirements.txt --fail-on-severity high
```

---

## 7. Architecture Decision Records (ADR'lar)

Her mimari karar bir ADR dosyası ile belgelenir. Format: `adr/ADR-<sequence>-<slug>.md`

### ADR-001 — Frontend: Vanilla JS (v4)

**Tarih:** 2024-06  
**Durum:** Kabul Edildi  
**AI Rolü:** co-decided

**Bağlam:** Vibecoding standartları React + TypeScript önerir. LaundroStar'ın mevcut Vanilla JS altyapısı ve küçük ölçeği değerlendirildi.

**Karar:** v4'te Vanilla JS modüler yapısı ile devam edilir. Öncelik güvenlik düzeltmeleri ve backend mimarisidir.

**Sonuç:** v5'te Next.js değerlendirmesi açık olarak tutulur.

---

### ADR-002 — JWT: RS256

**Tarih:** 2024-06  
**Durum:** Kabul Edildi  
**AI Rolü:** agent-proposed

**Bağlam:** v3'te HS256 kullanılıyordu. RS256, asimetrik imzalama ile public key paylaşımını güvenli kılar; private key sızması halinde imzasız token üretilemez.

**Karar:** RS256 kullanılır. Private/public key çifti env ile yönetilir.

**Sonuç:** Key yönetimi operasyonel yük; ancak ölçekte güvenlik kazancı büyük.

---

### ADR-003 — httpOnly Cookie ile Token Taşıma

**Tarih:** 2024-06  
**Durum:** Kabul Edildi  
**AI Rolü:** agent-proposed

**Bağlam:** v3'te token `localStorage`'da tutuluyordu; XSS saldırısında token çalınabilir.

**Karar:** Access token memory'de (AppState); refresh token httpOnly Secure cookie. CSRF double-submit pattern eklendi.

---

### ADR-004 — Alembic ile Migration

**Tarih:** 2024-06  
**Durum:** Kabul Edildi  
**AI Rolü:** agent-proposed

**Bağlam:** v3'te `Base.metadata.create_all()` ile şema oluşturuluyordu; bu production ortamında tutarsızlığa yol açabilir.

**Karar:** Alembic ile versiyonlanmış migration. `create_all()` yalnızca test ortamında izinli.
