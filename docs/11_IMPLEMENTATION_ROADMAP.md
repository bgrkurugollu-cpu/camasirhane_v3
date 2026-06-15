# LaundroStar — Uygulama Yol Haritası (v3 → v4)

> Bu doküman v3'ten v4'e geçiş fazlarını, her fazın kapsamını, bağımlılık grafiğini ve risk kayıtlarını tanımlar. Vibe coding modeliyle çalışılır: her faz agent session'larına bölünür; her session sonrası human gate ile ilerlenir.

---

## 1. Vibe Coding Çalışma Modeli

| Aktör | Sorumluluk |
|-------|-----------|
| **Developer** | Yön belirleme, karar verme, her faz sonunda human gate review, test onaylama |
| **Cursor / Claude Agent** | Kod yazımı, test yazımı, refactor, lint düzeltme |
| **11 Doküman** | Agent'ın bilgi tabanı; session başında ilgili doküman context'e yüklenir |

**Agent session akışı:**
```
1. Developer: intent belirler ("auth modülünü jwt httponly cookie ile yaz")
2. Developer: ilgili dokümanları context'e koyar
   - 07_SECURITY_IMPLEMENTATION (auth akışı)
   - 03_API_CONTRACTS (endpoint şemaları)
   - 04_BACKEND_SPEC (modül yapısı)
3. Developer: prompt yazar — net hedef + constraint
4. Agent: kod + test yazar
5. Agent: pytest + ruff çalıştırır; hata varsa düzeltir
6. Developer: review; kabul → commit; reject → iterate
7. PR → CI → squash merge
```

---

## 2. Bağımlılık Grafiği

```
Faz 0: Proje Scaffold (klasör yapısı, Dockerfile, CI)
   │
   ▼
Faz 1: DB Migration + Model Refactor (Alembic, model split, updated_at)
   │
   ▼
Faz 2: Auth Güvenlik Yükseltmesi (RS256, httpOnly cookie, CSRF, lockout)
   │
   ▼
Faz 3: Backend Modüler Refactor (router/service/repository, exception hierarchy)
   │
   ▼
Faz 4: API v1 + Response Envelope (prefix, PATCH, error codes, pagination)
   │
   ▼
Faz 5: Güvenlik Tamamlama (security headers, CORS, pip-audit CI, logging)
   │
   ▼
Faz 6: Frontend Güvenlik Düzeltmeleri (localStorage → memory, CSRF, innerHTML)
   │
   ▼
Faz 7: Test Coverage Tamamlama (unit + integration; gate %75)
   │
   ▼
Faz 8: Docker Hardening (multi-stage, non-root, .dockerignore)
   │
   ▼
Faz 9: Smoke Test + Staging Deploy
   │
   ▼
Faz 10: Kimlik & Güvenlik Entegrasyonları (MFA operasyonel + opsiyonel SSO)
```

> **Gate revizyonu (2026-06-07):** Faz 2–9 büyük ölçüde tamamlandı. Admin **MFA (TOTP)** backend'i uygulandı (ADR 0007); kalan operasyonel adımlar Faz 10'da toplandı. Ayrıntı için bkz. `REVIZYON_DOKUMANI.md`.

---

## 3. Faz Detayları

---

### Faz 0 — Proje Scaffold

#### Kapsam
- v4 dizin yapısını [[05_BACKEND_SPEC#2-klasör-yapısı--appsapi]] formatında oluştur
- `requirements.txt` güncelle: structlog, pytest-cov, ruff, mypy, pip-audit eklentileri
- `.env.example` güncelle: yeni key'ler (JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, ADMIN_PASSWORD_HASH)
- `pytest.ini` oluştur
- Temel CI pipeline: `.github/workflows/pr-check.yml` (lint + test + pip-audit)

#### Agent Kick-off Materyali
- `04_BACKEND_SPEC` — klasör yapısı
- `09_DEV_WORKFLOW` — Dockerfile kuralları, CI yapısı

#### Deliverable
- `apps/api/` dizini tam iskelet (her `__init__.py`, placeholder `router.py`, `service.py`)
- `docker compose up` başarılı
- `pytest` çalışır (0 test, 0 fail)

#### Human Gate
- [ ] Klasör yapısı `04_BACKEND_SPEC` ile birebir eşleşiyor
- [ ] `.env.example` tüm key'leri içeriyor
- [ ] CI pipeline tanımlı (lint + test)

---

### Faz 1 — DB Migration + Model Refactor

#### Kapsam
- `Base.metadata.create_all()` kaldır; Alembic kurulumu
- Model dosyalarını `models/` altında split et (`user.py`, `calisan.py`, `kiyafet.py`, `laundry.py`, `audit_log.py`)
- `users` tablosuna eksik alanlar ekle: `is_active`, `failed_login_count`, `locked_until`, `updated_at`
- `audit_logs` tablosuna: `ip_hash` ekle; `ip_address` kaldır
- `audit_logs` için append-only PostgreSQL RULE ekle
- `kirli_kiyafetler`, `temiz_kiyafetler`, `teslim_edilenler` tablolarına `created_by_user_id` ekle
- Başlangıç migration: `0001_initial_schema.py`

#### Agent Kick-off Materyali
- `02_DATABASE_SCHEMA` — tablo tanımları, migration stratejisi
- `01_DOMAIN_MODEL` — entity attribute'ları

#### Human Gate
- [ ] `alembic upgrade head` hatasız çalışıyor
- [ ] Tüm tablolar `02_DATABASE_SCHEMA` ile birebir eşleşiyor
- [ ] `audit_logs`'a UPDATE deneyince sessizce reddediliyor (RULE çalışıyor)
- [ ] Eski `create_all()` kodu kalmadı

#### Risk
- **Mevcut veri kaybı:** v3 DB'si varsa migration öncesi backup al. v4 temiz başlangıç önerilir.

---

### Faz 2 — Auth Güvenlik Yükseltmesi

#### Kapsam
- JWT: HS256 → RS256; `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` env
- Access token süresi: 1440 dk → 15 dk
- Refresh token oluştur: opaque, httpOnly Secure cookie, 7 gün, rotation
- Session tablosu: `sessions` tablosu oluştur (refresh_token_hash, ip_hash, expires_at, status)
- CSRF: double-submit cookie pattern; her login/refresh'te yeni token üret
- Hesap kilitleme: 5 hatalı giriş → 15 dk kilit (`failed_login_count`, `locked_until`)
- Şifre politikası: min 12 karakter Pydantic validator
- `POST /api/v1/auth/refresh` ve `POST /api/v1/auth/logout` endpoint'leri ekle
- Enumeration koruması: user-not-found ve wrong-password aynı mesaj

#### Agent Kick-off Materyali
- `07_SECURITY_IMPLEMENTATION` — auth akışı sekans diyagramları
- `03_API_CONTRACTS` — auth endpoint şemaları
- `02_DATABASE_SCHEMA` — sessions tablosu

#### Human Gate
- [ ] Login response'ta `refresh_token` body'de yok; yalnızca cookie
- [ ] Access token 15 dk sonra expire oluyor
- [ ] 5 hatalı giriş → hesap kilitilendiğini test et
- [ ] Token refresh çalışıyor (cookie ile)
- [ ] `test_auth.py` — tüm senaryolar yeşil

---

### Faz 3 — Backend Modüler Refactor

#### Kapsam
- `main.py` tek dosyadan modüllere bölme (bkz. [[05_BACKEND_SPEC#2-klasör-yapısı]])
- Her modül: `router.py` + `service.py` + `repository.py` + `schemas.py`
- `common/exceptions.py` → `AppException` hiyerarşisi
- `common/audit.py` → `write_audit_log()` helper (IP hash'leme dahil)
- `common/dependencies.py` → `get_current_user`, `require_admin`
- `common/response.py` → `success_response()` helper
- `init_mock_data` endpoint'ini **tamamen sil** (güvenlik açığı)
- `bootstrap/seed.py` → admin seed (env'den)

#### Agent Kick-off Materyali
- `04_BACKEND_SPEC` — modül iskeleti, pattern örnekleri
- `01_DOMAIN_MODEL` — audit action kodları

#### Human Gate
- [x] `main.py` yalnızca app factory; iş mantığı yok
- [x] Her endpoint'in karşılığı service fonksiyonu var
- [x] `init_mock_data` endpoint'i yok (404 dönüyor)
- [x] Tüm audit log yazmalar `write_audit_log()` üzerinden
- [x] `common/audit.py`: `ip_hash` SHA-256, plaintext IP yok

---

### Faz 4 — API v1 + Response Envelope

#### Kapsam
- Tüm endpoint URL'lerine `/api/v1/` prefix ekle
- Tüm `PUT` metodları → `PATCH`
- Response envelope: `{ "data": ... }` ve `{ "error": { "code": ..., "message": ... } }`
- Hata kodları standartlaştırma: `AUTH_*`, `USER_*`, `CALISAN_*`, `KIYAFET_*`, `ISLEM_*`
- Pagination: tablo endpoint'lerinde `offset`/`limit` + meta bilgisi
- `/api/tablo/{type}` → `/api/v1/tablo/{type}`
- `/api/islem/rfid-oku` → `/api/v1/islem/sepet-simulasyon` (daha açıklayıcı isim)

#### Agent Kick-off Materyali
- `03_API_CONTRACTS` — tam endpoint kataloğu, hata kodları

#### Human Gate
- [x] Tüm endpoint'ler `/api/v1/` ile başlıyor
- [x] `PUT` kullanan endpoint kalmadı
- [x] Tüm yanıtlar `{ "data": ... }` veya `{ "error": ... }` formatında
- [x] Frontend (`app.js`) yeni URL'leri ve envelope formatını kullanıyor

---

### Faz 5 — Güvenlik Tamamlama

#### Kapsam
- `SecurityHeadersMiddleware` — X-Frame-Options, CSP, X-Content-Type-Options, HSTS
- CORS middleware — strict allowlist
- `slowapi` rate limiting tüm kritik endpointlere uygulandı (bkz. [[08_SECURITY_IMPLEMENTATION#7-rate-limiting]])
- `structlog` ile JSON logging kurulumu
- `pip-audit` CI adımına eklendi
- Profil fotoğrafı: magic byte kontrolü eklendi

#### Agent Kick-off Materyali
- `07_SECURITY_IMPLEMENTATION` — header'lar, rate limit tablosu, logging kuralları

#### Human Gate
- [x] Response header'larında X-Frame-Options: DENY var
- [x] Login 10/dk limitini aşınca 429 dönüyor
- [x] Log çıktısı JSON formatında (Pino değil structlog)
- [x] `pip-audit` CI adımı yeşil

---

### Faz 6 — Frontend Güvenlik Düzeltmeleri

#### Kapsam
- `localStorage.setItem('token', ...)` → **tamamen kaldır**
- `AppState.accessToken` (memory) → `api.js` wrapper ile kullanım
- CSRF token: her mutating request'te `X-CSRF-Token` header
- `innerHTML` kullanımı → `textContent`/güvenli DOM API ile değiştir
- Token refresh interceptor: 401 AUTH_TOKEN_EXPIRED → silent refresh
- JS modüler split: `app.js` tek dosyadan `js/modules/` yapısına (bkz. [[06_FRONTEND_SPEC#2-klasör-yapısı]])
- Yeni API URL'leri ve response envelope uyumluluğu

#### Agent Kick-off Materyali
- `05_FRONTEND_SPEC` — state yönetimi, api wrapper, güvenlik kuralları
- `03_API_CONTRACTS` — yeni endpoint URL'leri

#### Human Gate
- [x] Browser DevTools → Application → Local Storage → `token` alanı yok
- [x] Login'den sonra token yalnızca memory'de (AppState)
- [x] Sayfa yenilenince login ekranı gelir (token kaybolur — beklenen)
- [x] Mutating request'lerde `X-CSRF-Token` header gönderiliyor

---

### Faz 7 — Test Coverage Tamamlama

#### Kapsam
- Auth modülü: %90+ line coverage (lockout, refresh, logout, CSRF testleri)
- İşlem akışı: %85+ (kirli→temiz→teslim uçtan uca)
- Shelf service: %95+ (cinsiyet kuralı, kapasite sınırı)
- Genel %75 gate → CI pass

#### Agent Kick-off Materyali
- `08_TESTING_STRATEGY` — test senaryoları, conftest fixture'ları

#### Human Gate
- [x] `pytest --cov-fail-under=75` yeşil
- [x] `test_init_mock_data_not_exists` — 404 dönüyor
- [x] `test_no_plaintext_ip_in_audit` — ip_hash SHA-256 uzunluğu
- [x] `test_security_headers_present` — X-Frame-Options var

---

### Faz 8 — Docker Hardening

#### Kapsam
- Dockerfile → multi-stage build (builder + production)
- Non-root user (`appuser`)
- `.dockerignore` oluştur
- `docker-compose.yml` güncelle: env_file, health check, restart policy
- Production `SECRET_KEY` ve JWT key'leri güçlü değerlerle belgelenmiş (örnek değil)

#### Agent Kick-off Materyali
- `09_DEV_WORKFLOW` — Dockerfile kuralları

#### Human Gate
- [x] `docker build` başarılı
- [x] `docker run --user` → non-root kullanıcı çalışıyor
- [x] Image içinde `.env` dosyası yok
- [x] Healthcheck başarılı

---

### Faz 9 — Smoke Test + Staging Deploy

#### Kapsam
- `docker compose up` tam ortam
- Manuel smoke test: login, kirli giriş, onay, teslim döngüsü
- Audit log kayıtları doğrulama
- Dashboard grafik render kontrol

#### Human Gate
- [ ] Uçtan uca kıyafet döngüsü çalışıyor
- [ ] Audit log'da IP plaintext yok
- [ ] Security header'lar browser DevTools'da görünüyor
- [ ] Token localStorage'da yok

---

### Faz 10 — Kimlik & Güvenlik Entegrasyonları

> Bağlam: Admin MFA (TOTP) backend'i Faz 2 sonrası gate revizyonunda eklendi (ADR 0007). Bu faz, MFA'yı **operasyonel** hale getirmeyi ve (yalnızca kurumsal ağa geçilecekse) **SSO** entegrasyonunu kapsar. SSO bir mimari sapma kararıdır (ADR 0003) ve MFA'dan bağımsızdır.

#### Alt Aşama A — MFA'yı Devreye Alma (standalone kalsa bile gerekli)

Kapsam:
- **A1 — MFA kayıt UI'ı:** "Güvenlik" menüsüne kurulum ekranı. `POST /auth/mfa/setup`'tan dönen `otpauth_uri` QRious ile QR'a çevrilir; kod input'u + "Etkinleştir" (`/auth/mfa/activate`) ve "Kapat" (`/auth/mfa/disable`) butonları.
- **A2 — Zorunlu kılma:** `.env` `ADMIN_MFA_REQUIRED=true`; tüm admin'leri authenticator'a kaydettir.
- **A3 — MFA reset ucu:** Admin'in başka bir admin'in MFA'sını sıfırlaması (`mfa_enabled=0, mfa_secret=NULL`) — cihaz kaybı senaryosu.
- **A5 — Kalıcı migration:** `mfa_enabled` / `mfa_secret` kolonlarını manuel `ALTER` yerine **Alembic migration**'a taşı.

#### Alt Aşama B — SSO (yalnızca kurumsal ağa geçilecekse)

Kapsam:
- **B1 — Karar/ADR:** ADR 0003'ü revize et (standalone mı, kurumsal mı). Kapalı-devre kalacaksa bu alt aşama atlanır.
- **B2 — Keycloak kurulumu:** realm + client (Authorization Code + PKCE), redirect URI'ler, client secret.
- **B3 — Backend (authlib zaten kurulu):** Keycloak JWKS ile token doğrulama; roller realm/client-role'den map'lenir; `get_current_user` Keycloak public key'ini de kabul edecek şekilde genişletilir (DI yapısı uygun).
- **B4 — Frontend:** Login modal yerine Keycloak redirect + callback handling.
- **B5 — MFA çakışması:** SSO'ya geçilince app-level TOTP **kapatılır** (MFA Keycloak'ta yönetilir).

#### Alt Aşama C — Sertleştirme (v5)
- `mfa_secret` encryption-at-rest (uygulama anahtarıyla şifrele); recovery/yedek kodları.

#### Agent Kick-off Materyali
- `08_SECURITY_IMPLEMENTATION` — MFA akışı (§2.4), JWT/SSO
- `docs/adr/0003-keycloak-bagimsiz-auth.md`, `docs/adr/0007-admin-mfa-totp.md`
- `03_API_CONTRACTS` — `/auth/mfa/*` sözleşmeleri (§3.1.1)

#### Önerilen Sıra
**A → (gerekirse) B.** Çoğu senaryoda A yeterlidir; B ancak uygulama fabrika dışına/kurumsal ekosisteme taşınırsa anlamlıdır.

#### Human Gate
- [ ] A1: Admin, Güvenlik ekranından QR okutup MFA'yı etkinleştirebiliyor; sonraki login'de TOTP isteniyor
- [ ] A2: `ADMIN_MFA_REQUIRED=true` ve tüm admin'ler kayıtlı
- [ ] A3: MFA reset ucu yalnızca admin'e açık ve audit'leniyor
- [ ] A5: `alembic upgrade head` MFA kolonlarını üretiyor (manuel ALTER kaldırıldı)
- [ ] B (varsa): Keycloak ile login çalışıyor; app-level TOTP kapatıldı; ADR 0003 revize edildi

---

## 4. Risk Kaydı

| Risk | Olasılık | Etki | Önlem |
|------|----------|------|-------|
| v3 verisinin v4'e migrasyon uyumsuzluğu | Orta | Yüksek | v4 temiz başlangıç; v3 DB yedekle |
| Frontend token memory'de → sayfa yenileme zorluğu | Düşük | Orta | Refresh token cookie ile otomatik yenileme; UX kabul edilebilir |
| RS256 anahtar yönetimi operasyonel karmaşıklığı | Orta | Düşük | `generate-jwt-keys.sh` scripti; dokümantasyon |
| Raf atama algoritması cinsiyet kuralı regression | Düşük | Yüksek | %95+ test coverage hedefi (Faz 7) |
| `localhost` HTTPS sertifikası self-signed uyarısı | Yüksek | Düşük | Dev'de HTTP kabul edilebilir; Nginx sadece staging/prod için |

---

## 5. Teknik Borç Kaydı

| Borç                                               | Faz          | Not                                                                                                            |
| -------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------- |
| React/Next.js frontend migrasyonu                  | v5           | ADR-001                                                                                                        |
| Şifre geçmişi (son 5 şifre tekrar kullanım engeli) | v5           | Auth modülü genişlemesi                                                                                        |
| HIBP şifre kontrolü                                | v5           | Dış API bağımlılığı                                                                                            |
| MFA (TOTP) admin için                              | **Faz 10-A** | Backend + login akışı uygulandı (ADR 0007). Kalan: kayıt UI (A1), zorunlu kılma (A2), reset (A3), Alembic (A5) |
| Keycloak SSO entegrasyonu                          | Faz 10-B     | Yalnızca kurumsal ağa geçilecekse; ADR 0003 revizyonu gerektirir. `authlib` hazır                              |
| MFA secret encryption-at-rest + recovery kodları   | v5           | Faz 10-C                                                                                                       |
| Gerçek RFID donanım entegrasyonu                   | v5           | Donanım satın alımı gerektirir                                                                                 |
| SAP/İK entegrasyonu                                | v5           | —                                                                                                              |
| Audit log retention job (6 ay TTL)                 | v4.1         | Cron job                                                                                                       |
| Şifre sıfırlama email akışı                        | v4.1         | SMTP altyapısı gerektirir                                                                                      |
| Row-Level Security (PostgreSQL RLS)                | v5           | Multi-tenant ihtiyacı olmadığı sürece ertelendi                                                                |
| Centralized log aggregation (ELK/Loki)             | v5           | v4'te structlog JSON yeterli                                                                                   |
