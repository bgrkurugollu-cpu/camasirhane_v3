# LaundroStar — Test Stratejisi

> Bu doküman test piramidini, araçları, coverage hedeflerini ve PR öncesi self-check listesini tanımlar. Agent test yazarken bu dokümandaki kuralları izler.

---

## 1. Test Piramidi

```
         /\
        /E2E\        %10 — kritik akışlar
       /------\
      / Integr.\    %20 — API endpoint + DB
     /----------\
    /    Unit    \  %70 — service, repository, utility
   /______________\
```

---

## 2. Araçlar

| Seviye | Araç | Açıklama |
|--------|------|----------|
| Unit + Integration | `pytest` 8+ | Python native test framework |
| Coverage | `pytest-cov` | `--cov=app --cov-report=xml` |
| Test DB | PostgreSQL (`TEST_DATABASE_URL`) → yoksa SQLite fallback | Integration testler tercihen gerçek Postgres'e karşı (timezone/JSON paritesi); CI'da testcontainers ile sağlanır. Her test fonksiyonu şemayı sıfırlayarak izole çalışır. |
| HTTP Client | `httpx.AsyncClient` / FastAPI `TestClient` | Endpoint testleri |
| Mock | `unittest.mock` | Dış bağımlılık izolasyonu |
| Lint | `ruff` | Hızlı Python linter |
| Type check | `mypy` | Static type analysis |
| Dep tarama | `pip-audit` | CI'da high/critical = fail |

---

## 3. Coverage Hedef Matrisi

| Modül | Line Coverage | Branch Coverage | Gerekçe |
|-------|--------------|-----------------|---------|
| `modules/auth/` | %90+ | %85+ | Kritik güvenlik modülü |
| `modules/islem/` (iş akışı) | %85+ | %80+ | Core business logic |
| `common/security_headers.py` | %90+ | — | Güvenlik altyapısı |
| `modules/islem/shelf_service.py` | %95+ | %90+ | Algoritma hatası direkt operasyonel etki |
| Diğer modüller | %70+ | — | CRUD modülleri |
| **Genel ortalama** | **%80+** | — | CI gate |

**CI gate:** `pytest --cov=app --cov-fail-under=80` — fail olursa merge bloklanır. (Uygulanan `pytest.ini` ile birebir tutarlı; mevcut ölçülen coverage **%85**.)

---

## 4. Unit Test Kuralları

- Her `service.py` fonksiyonu için en az bir unit test.
- DB bağımlılıkları `Mock` veya in-memory SQLite ile izole edilir.
- Test dosyası ile kaynak dosyası `tests/` klasöründe yan yana bulunur.
- Test adı: `test_<fonksiyon_adı>_<senaryo>` formatı.

**Örnek — Shelf Service:**

```python
# modules/islem/tests/test_shelf_service.py
from unittest.mock import MagicMock, patch
from modules.islem.shelf_service import assign_shelf

def test_assign_shelf_female_uses_e_rack():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
    result = assign_shelf(mock_db, cinsiyet='K')
    assert result is not None
    assert result.startswith('E')

def test_assign_shelf_male_excludes_e_rack():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
    result = assign_shelf(mock_db, cinsiyet='E')
    assert result is not None
    assert not result.startswith('E')

def test_assign_shelf_returns_none_when_full():
    mock_db = MagicMock()
    # Tüm gözleri dolu simüle et
    all_slots = [
        (f"{l}{f}{c}", 3 if f < 7 else 1)
        for l in 'ABCDFGH'
        for f in range(1, 8)
        for c in range(1, 6)
    ]
    mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = all_slots
    result = assign_shelf(mock_db, cinsiyet='E')
    assert result is None
```

---

## 5. Integration Test Kuralları

- Endpoint testleri FastAPI `TestClient` ile yapılır.
- Test veritabanı: `TEST_DATABASE_URL` verilirse gerçek PostgreSQL; yoksa lokal hızlı çalışma için SQLite fallback. **CI'da PostgreSQL zorunludur** (servis container; bkz. §8). Böylece `DateTime(timezone=True)`, `audit_logs` RULE'leri gibi PG'ye özgü davranışlar gerçek motorda doğrulanır.
- Her test **fonksiyonu** öncesi şema sıfırlanır (`drop_all`/`create_all`) ve deterministik seed yüklenir → tam izolasyon.
- `conftest.py`'da `client`, `db_session`, `admin_token`, `user_token` fixture'ları tanımlıdır.

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")  # CI'da Postgres

@pytest.fixture(scope="session")
def test_db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db):
    SessionLocal = sessionmaker(bind=test_db)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Kritik integration test senaryoları:**

| Test | Kapsam |
|------|--------|
| `test_login_success` | Başarılı login; token döner; audit log yazılır |
| `test_login_fail_wrong_password` | Hatalı şifre; 401; failed_login_count artar |
| `test_login_lockout` | 5 hatalı giriş → hesap kilitlenir |
| `test_token_refresh` | Geçerli refresh cookie ile yeni token |
| `test_refresh_revoked_session` | Revoke edilmiş session ile 401 |
| `test_kirli_giris_rfid_not_found` | Kayıtsız RFID ile 404 |
| `test_full_laundry_flow` | Kirli → Onayla → Teslim döngüsü uçtan uca |
| `test_shelf_assignment_gender_rule` | Kadın kıyafeti E rafına; erkek E dışına |
| `test_shelf_full_returns_409` | Tüm raflar doluyken 409 |
| `test_admin_only_endpoint_as_user` | User ile admin endpoint'e → 403 |
| `test_mfa_required_after_enable` | MFA aktifken login `mfa_required` döner, access_token vermez (ADR 0007) |
| `test_mfa_verify_success` / `_wrong_code` | TOTP 2. faktör doğru/yanlış kod akışı |
| `test_teslim_sicil_mismatch` | Yanlış sicil ile teslim → 400 |
| `test_rfid_delete_with_open_records` | Açık kirli kaydı varken RFID sil → 409 |
| `test_init_mock_data_not_exists` | `/api/init_mock_data` endpoint'i yok → 404 |

---

## 6. Audit Log Doğrulama

Her state-changing aksiyon sonrası ilgili AuditLog kaydının oluştuğunu doğrula:

```python
def test_kirli_giris_creates_audit_log(client, db_session):
    # ... kirli giriş yap
    log = db_session.query(AuditLog).filter_by(action="KIRLI_GIRIS").first()
    assert log is not None
    assert log.username == "testuser"
    assert log.status == "success"
    assert log.ip_hash is not None          # IP hash'lendi
    assert len(log.ip_hash) == 64           # SHA-256 hex uzunluğu
```

---

## 7. Güvenlik Testleri

| Test | Kapsam |
|------|--------|
| `test_no_plaintext_ip_in_audit` | audit_logs.ip_hash SHA-256 uzunluğu |
| `test_csrf_required_for_mutation` | CSRF header olmadan POST/PATCH/DELETE → 403 |
| `test_password_min_length` | 11 karakter şifre → 422 |
| `test_token_not_in_response_body` | Login response'ta refresh_token yok |
| `test_admin_endpoint_requires_auth` | Token olmadan → 401 |
| `test_security_headers_present` | X-Frame-Options, CSP, X-Content-Type-Options header'ları |

---

## 8. CI Pipeline

Uygulanan workflow: `.github/workflows/ci.yml`. İki job vardır:

**`test` job** — testleri **gerçek PostgreSQL** servis container'ına karşı koşar:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env: { POSTGRES_USER: camasirhane, POSTGRES_PASSWORD: testpass, POSTGRES_DB: camasirhane_test }
    ports: [ "5432:5432" ]
    options: >-
      --health-cmd "pg_isready -U camasirhane -d camasirhane_test"
      --health-interval 10s --health-timeout 5s --health-retries 10
env:
  DATABASE_URL: postgresql://camasirhane:testpass@localhost:5432/camasirhane_test
  TEST_DATABASE_URL: postgresql://camasirhane:testpass@localhost:5432/camasirhane_test
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with: { python-version: "3.12", cache: pip }
  - run: pip install -r requirements.txt
  - name: Generate RS256 test keys   # certs/ .gitignore'da; CI'da geçici üretilir
    run: |
      mkdir -p certs
      openssl genpkey -algorithm RSA -out certs/private_key.pem -pkeyopt rsa_keygen_bits:2048
      openssl rsa -in certs/private_key.pem -pubout -out certs/public_key.pem
  - run: pytest   # pytest.ini → --cov-fail-under=80
```

**`security-audit` job** — bağımlılık taraması (high/critical → fail):

```yaml
- run: pip install pip-audit
- run: pip-audit -r requirements.txt
```

> Not: Testler hem PostgreSQL (CI) hem SQLite (lokal fallback) altında yeşildir.
> `audit_logs` append-only RULE'ü yalnızca PostgreSQL'de oluşur (`app/database.py`
> connect event listener); SQLite'ta atlanır.

---

## 9. PR Öncesi Self-Check

PR açmadan önce:

- [ ] `pytest` yeşil (tüm testler geçiyor)
- [ ] Coverage %80+ (CI gate)
- [ ] `ruff check` yeşil (lint hatasız)
- [ ] Yeni endpoint varsa: integration test yazıldı
- [ ] Yeni iş kuralı varsa: unit test yazıldı
- [ ] Güvenlik-kritik değişiklik varsa: güvenlik testi yazıldı
- [ ] `init_mock_data` veya benzeri auth-gerektirmeyen endpoint eklenmedi
- [ ] Token `localStorage`'a yazılmıyor
