# LaundroStar — Güvenlik Uygulaması

> Bu doküman güvenliğin koda ve altyapıya nasıl yansıdığını anlatır. Güvenlik-bilinçli bir agent burada yazılanı birebir uygular: aynı JWT algoritmasını, aynı rate limit değerlerini, aynı CSRF kontrol kurallarını kullanır.

---

## 1. Kapsam ve Katmanlama

Güvenlik beş katmanda uygulanır; hiçbiri tek başına yeterli değildir:

| Katman | Kontroller |
|--------|-----------|
| **Ağ** | Nginx reverse proxy; uygulama doğrudan internete açık değil; TLS 1.2/1.3 |
| **Altyapı** | Docker Multi-stage build, non-root user (`appuser`) profili ile izolasyon |
| **Uygulama Sınırı** | JWT doğrulama, CSRF, rate limit, CORS, Pydantic validation |
| **Domain / İş Mantığı** | Rol kontrolü (require_admin), resource ownership, state machine kuralları |
| **Veritabanı** | Audit log append-only rule; IP hash storage; bcrypt |
| **Gözlemlenebilirlik** | Structured logging, audit log, başarısız giriş sayacı |

---

## 2. Kimlik Doğrulama Akışı

### 2.1 Login (Email + Şifre)

```
POST /api/v1/auth/login

1. Rate limit kontrol: 10/dakika per IP
2. Pydantic validation (username, password zorunlu)
3. DB'den user çek: WHERE username = ? AND is_active = true
4. User bulunamazsa: AuditLog(LOGIN_FAIL) → 401 AUTH_INVALID_CREDENTIALS
   [Enumeration koruması: "bulunamadı" ile "hatalı şifre" aynı mesaj]
5. locked_until > NOW() kontrolü: 401 AUTH_ACCOUNT_LOCKED {unlocks_at}
6. bcrypt.verify(password, hashed_password)
7. Yanlış şifre:
   - failed_login_count += 1
   - count >= 5: locked_until = NOW() + 15dk; AuditLog(LOGIN_LOCKED)
   - AuditLog(LOGIN_FAIL) → 401 AUTH_INVALID_CREDENTIALS
8. Başarılı:
   - failed_login_count = 0
   - Access token üret (RS256, 15 dk)
   - Refresh token üret (opaque, 7 gün)
   - Session kaydı DB'ye yaz (refresh_token_hash, ip_hash, user_agent)
   - AuditLog(LOGIN_SUCCESS)
   - Response: {access_token, csrf_token, user}
   - Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh
```

### 2.2 Token Refresh

```
POST /api/v1/auth/refresh
Cookie: refresh_token=...
Header: X-CSRF-Token: ...

1. CSRF token doğrula
2. Cookie'den refresh token oku
3. DB'den session bul: WHERE refresh_token_hash = SHA256(token)
4. Session bulunamazsa: 401 AUTH_SESSION_REVOKED
5. Session status REVOKED ise: 401 AUTH_SESSION_REVOKED
6. expires_at geçmiş mi: 401 AUTH_SESSION_REVOKED
7. Yeni access token üret (RS256, 15 dk)
8. Yeni refresh token üret (rotation); DB güncelle
9. AuditLog(TOKEN_REFRESH)
10. Response: yeni {access_token, csrf_token}
    Set-Cookie: refresh_token=...(yeni); HttpOnly; Secure; SameSite=Strict
```

### 2.3 Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
Header: X-CSRF-Token: ...

1. CSRF token doğrula
2. Access token decode → session_id
3. DB'de session REVOKED yap
4. AuditLog(LOGOUT)
5. Set-Cookie: refresh_token=; Max-Age=0 (clear)
6. Response: 204
```

---

### 2.4 Admin MFA — TOTP İkinci Faktör (ADR 0007)

Admin (ve isteğe bağlı tüm) hesaplar için `pyotp` tabanlı TOTP (RFC 6238) ikinci faktörü uygulanmıştır.

```
POST /api/v1/auth/token            → şifre doğru + MFA aktif ise:
                                     { "mfa_required": true, "mfa_token": <5dk, type=mfa> }
POST /api/v1/auth/mfa/verify       → { mfa_token, code } doğru ise oturum açılır
POST /api/v1/auth/mfa/setup        → (auth) secret + otpauth:// URI (QR)
POST /api/v1/auth/mfa/activate     → (auth) { code } ile etkinleştir
POST /api/v1/auth/mfa/disable      → (auth) geçerli { code } ile kapat
```

- `User.mfa_enabled` (0/1) ve `User.mfa_secret` (base32) alanları eklenmiştir.
- `mfa_token` access token değildir; yalnızca `type='mfa'` taşır ve sadece `/auth/mfa/verify` ile kullanılır.
- `ADMIN_MFA_REQUIRED=true` iken MFA tanımlamamış admin login yanıtında `mfa_enrollment_required` uyarısı alır.
- Saat kayması toleransı: `valid_window=1` (±30 sn). Audit olayları: `MFA_SETUP_START`, `MFA_ENABLED`, `MFA_SUCCESS`, `MFA_FAIL`, `MFA_DISABLED`, `LOGIN_MFA_CHALLENGE`.

## 3. JWT Spesifikasyonu

| Parametre | Değer |
|-----------|-------|
| Algoritma | RS256 |
| Access token süresi | 15 dakika |
| Refresh token süresi | 7 gün |
| Access token taşıma | `Authorization: Bearer` header |
| Refresh token taşıma | httpOnly Secure SameSite=Strict Cookie |
| JWT claims (access) | `sub` (username), `uid` (user_id), `role`, `sid` (session_id), `exp`, `iat` |

**RS256 anahtar yönetimi:**
- Private key: `JWT_PRIVATE_KEY` env variable (PEM format)
- Public key: `JWT_PUBLIC_KEY` env variable
- Anahtar boyutu: minimum 2048 bit
- Rotasyon: manuel; rotasyon sırasında eski public key kısa süre paralel tutulabilir

**CSRF Token:**
- Her login ve her refresh'te yeni üretilir.
- Format: `secrets.token_urlsafe(32)` (Python)
- Frontend `AppState.csrfToken` değişkeninde memory'de tutar.
- Mutating endpoint'lerde `X-CSRF-Token` header zorunludur; backend cookie'deki CSRF değeri ile karşılaştırır (double-submit cookie pattern).

---

## 4. Şifre Politikası

| Kural | Değer |
|-------|-------|
| Minimum uzunluk | 12 karakter |
| bcrypt cost factor | 12 |
| Maksimum hatalı giriş | 5 |
| Kilit süresi | 15 dakika |
| Şifre geçmişi | v4'te yok (v5'te eklenir) |
| HIBP kontrolü | v5 planında |

Şifre validasyonu `Pydantic` validator ile yapılır:

```python
from pydantic import field_validator

@field_validator('password')
def password_strength(cls, v):
    if len(v) < 12:
        raise ValueError('Şifre en az 12 karakter olmalıdır.')
    return v
```

---

## 5. Yetkilendirme

### 5.1 Rol Modeli

İki rol: `admin` ve `user`. Rol koda sabit enum olarak tanımlanır:

```python
# models/user.py
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
```

### 5.2 Yetki Kontrol Katmanları

1. **Kimlik doğrulama:** `get_current_user` dependency — token geçerli mi, user aktif mi.
2. **Rol kontrolü:** `require_admin` dependency — yalnızca admin rolü gerekiyorsa.
3. **Resource ownership:** Service katmanında — kullanıcı kendi kaynağına mı erişiyor (örn. kendi profili).

### 5.3 Admin Gerektiren Endpointler

- `GET /api/v1/users` — Tüm kullanıcılar
- `POST /api/v1/users` — Kullanıcı oluştur
- `PATCH /api/v1/users/{user_id}` — Başka kullanıcı güncelle
- `DELETE /api/v1/users/{user_id}` — Kullanıcı sil
- `POST /api/v1/kiyafetler` — RFID eşleştir
- `PATCH /api/v1/kiyafetler/{rfid_tag}` — RFID güncelle
- `DELETE /api/v1/kiyafetler/{rfid_tag}` — RFID sil
- `GET /api/v1/tablo/teslim` — Teslim geçmişi
- `GET /api/v1/tablo/kiyafet` — Kıyafet listesi
- `GET /api/v1/audit-logs` — Audit loglar

> MFA uçları (`/api/v1/auth/mfa/setup|activate|disable`) admin-only değildir; her oturum sahibi kendi MFA'sını yönetir. Ancak admin hesaplarında MFA **operasyonel olarak zorunludur** (ADR 0007).

---

## 6. Güvenlik Header'ları

Her HTTP yanıtına `SecurityHeadersMiddleware` tarafından eklenir:

```python
# common/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'nonce-{nonce}' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
```

---

## 7. Rate Limiting

`slowapi` ile IP bazlı rate limiting:

| Endpoint | Limit |
|----------|-------|
| `POST /api/v1/auth/login` | 10/dakika per IP |
| `POST /api/v1/auth/refresh` | 30/dakika per IP |
| `POST /api/v1/users/me/photo` | 10/dakika per user |
| `POST /api/v1/islem/*` | 60/dakika per user |
| Diğer (genel) | 200/dakika per IP |

Rate limit aşımında: `429 RATE_LIMIT_EXCEEDED` + `retry_after_seconds`.

---

## 8. CORS Politikası

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # production: strict allowlist
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "X-CSRF-Token", "Content-Type", "X-Request-Id"],
)
```

Development ortamında `allow_origins=["http://localhost:8086"]`. Wildcard `*` **yasaktır**.

---

## 9. Input Validasyonu

Tüm request body'leri Pydantic v2 ile validate edilir. Pydantic validation hatası → `422 VALIDATION_FAILED` + field bazlı hata detayı.

**Kural:** Backend her zaman kendi validasyonunu yapar; frontend validasyonu yalnızca UX içindir.

```python
class KirliGirisRequest(BaseModel):
    rfid_tag: str = Field(..., min_length=1, max_length=50, pattern=r'^[A-Za-z0-9\-]+$')
```

---

## 10. Profil Fotoğrafı Güvenliği

```python
async def upload_photo(file: UploadFile, current_user: User, db: Session):
    # 1. Content-Type kontrolü
    if file.content_type != "image/png":
        raise AppException("USER_PHOTO_INVALID_FORMAT", 400)

    # 2. Dosya boyutu kontrolü (max 2 MB)
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise AppException("USER_PHOTO_TOO_LARGE", 400)

    # 3. Magic byte kontrolü (PNG imzası: \x89PNG)
    if not contents.startswith(b'\x89PNG\r\n\x1a\n'):
        raise AppException("USER_PHOTO_INVALID_FORMAT", 400)

    # 4. Güvenli dosya adı (kullanıcı girdisi kullanılmaz)
    filename = f"avatar_{current_user.id}_{secrets.token_hex(8)}.png"
    filepath = os.path.join(settings.upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)
```

---

## 11. Audit Log Güvenliği

- `audit_logs` tablosuna PostgreSQL `RULE` ile UPDATE ve DELETE engellenir (bkz. [[03_DATABASE_SCHEMA#57-audit_logs]]).
- Her kayıt `write_audit_log()` helper'ı üzerinden yazılır.
- IP adresi hash'lenerek saklanır; plaintext IP tabloya yazmaz.
- Audit log API yanıtında `ip_hash` alanı döndürülmez.

---

## 12. Secret Yönetimi

| Secret | Konum | Kural |
|--------|-------|-------|
| `DATABASE_URL` | `.env` → Docker secret | Kod içinde hardcoded yasak |
| `SECRET_KEY` (CSRF/session) | `.env` | Min 32 byte random |
| `JWT_PRIVATE_KEY` | `.env` (PEM) | Min 2048 bit RSA |
| `JWT_PUBLIC_KEY` | `.env` | — |
| `ADMIN_PASSWORD_HASH` | `.env` | bcrypt önceden hash edilmiş |

**Kural:** `.env` dosyası `.gitignore`'da. `.env.example` içinde tüm key'ler örnek değerlerle (gerçek değer yok) listelenmiştir. Kod içinde sabit secret string **yoktur**.

---

## 13. Güvenlik Açığı Tarama (CI)

Her PR'da:
```bash
pip-audit --requirement requirements.txt --fail-on-severity high
```

`high` veya `critical` severity bulunan dependency → CI pipeline fail olur; merge yapılamaz.
