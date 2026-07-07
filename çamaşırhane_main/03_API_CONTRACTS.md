# LaundroStar — API Kontratları

> Bu doküman tüm REST endpoint'leri, request/response şemalarını, hata kodları taksonomiyi ve versiyonlama kurallarını tanımlar. Agent yeni endpoint açarken veya frontend fetch kodu yazarken bu dokümanı tek referans alır.

---

## 1. Genel Kurallar

### 1.1 Versiyonlama

Tüm endpoint'ler `/api/v1/` prefix'i ile başlar.

```
/api/v1/auth/login
/api/v1/users/me
/api/v1/islem/kirli-giris
```

### 1.2 URL ve JSON Stili

- URL: `kebab-case` (örn. `/kirli-giris`, `/raf-detay`)
- JSON alanları: `snake_case` (Python/FastAPI default)
- HTTP metodlar: `GET`, `POST`, `PATCH`, `DELETE`. **`PUT` kullanılmaz.**

### 1.3 Response Envelope

Başarılı tüm yanıtlar `data` wrapper ile döner:

```json
{
  "data": { ... }
}
```

Liste endpoint'leri:
```json
{
  "data": [ ... ],
  "meta": {
    "total": 150,
    "offset": 0,
    "limit": 50
  }
}
```

Hata yanıtları:
```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Kullanıcı adı veya şifre hatalı.",
    "request_id": "req_abc123"
  }
}
```

### 1.4 Auth Gereksinimleri

`POST /api/v1/auth/login`, `POST /api/v1/auth/refresh` ve ilk kurulum uçları (`GET /api/v1/auth/bootstrap-status`, `POST /api/v1/auth/bootstrap`) dışındaki tüm endpoint'ler geçerli access token gerektirir. Bootstrap uçları yalnızca sistemde hiç kullanıcı yokken anlamlıdır (bkz. §3.1.2).

Access token: `Authorization: Bearer <token>` header'ı.

Admin gerektiren endpoint'ler ayrıca role kontrolü yapar; yetersiz yetki → `403 AUTH_FORBIDDEN`.

### 1.5 İdempotency

State değiştiren POST endpoint'lerinde `X-Idempotency-Key` header'ı isteğe bağlı olarak gönderilebilir. Aynı key ile tekrar gelen istek önbelleğe alınmış yanıtı döner (60 saniye TTL, Redis).

---

## 2. Hata Kodları Taksonomisi

### Auth Hataları

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Hatalı kullanıcı adı veya şifre |
| `AUTH_ACCOUNT_LOCKED` | 401 | Hesap kilitlendi; `unlocks_at` alanı döner |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token süresi doldu |
| `AUTH_TOKEN_INVALID` | 401 | Token geçersiz veya imzası bozuk |
| `AUTH_SESSION_REVOKED` | 401 | Session iptal edildi |
| `AUTH_FORBIDDEN` | 403 | Yetki yetersiz |
| `AUTH_CSRF_INVALID` | 403 | CSRF token eşleşmedi |

### Validasyon Hataları

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `VALIDATION_FAILED` | 422 | Request body/query parametre hatası; `details` alanında field bazlı hata listesi |

### User Hataları

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `USER_NOT_FOUND` | 404 | Kullanıcı bulunamadı |
| `USER_USERNAME_TAKEN` | 409 | Bu kullanıcı adı zaten kullanımda |
| `USER_CANNOT_DELETE_SELF` | 400 | Kendi hesabını silemezsin |
| `USER_LAST_ADMIN` | 400 | Son admin silinemez / pasifleştirilemez |
| `USER_PHOTO_INVALID_FORMAT` | 400 | Desteklenmeyen dosya formatı |
| `USER_PHOTO_TOO_LARGE` | 400 | Dosya boyutu limitini aşıyor |

### Calisan Hataları

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `CALISAN_NOT_FOUND` | 404 | Personel bulunamadı |
| `CALISAN_REQUIRED_FIELDS` | 400 | Yeni personel için ad/soyad zorunlu |

### Kıyafet Hataları

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `KIYAFET_RFID_TAKEN` | 409 | Bu RFID tag zaten başka sicile bağlı |
| `KIYAFET_NOT_FOUND` | 404 | RFID kaydı bulunamadı |
| `KIYAFET_HAS_OPEN_RECORDS` | 409 | Açık kirli/temiz kaydı var; silinemez |

### İşlem Hataları

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `ISLEM_RFID_NOT_REGISTERED` | 404 | Bu RFID tag sistemde kayıtlı değil |
| `ISLEM_KIRLI_NOT_FOUND` | 404 | Kirli kayıt bulunamadı |
| `ISLEM_TEMIZ_NOT_FOUND` | 404 | Temiz kayıt bulunamadı |
| `ISLEM_SICIL_MISMATCH` | 400 | Sicil numarası eşleşmiyor |
| `ISLEM_SEPET_BOS` | 200 | Sepette yeni kıyafet yok (hata değil; data.durum ile bildirilir) |
| `ISLEM_SHELF_FULL` | 409 | Uygun raf bölmesi yok; kapasite dolu |

### Rate Limit

| Kod | HTTP | Açıklama |
|-----|------|----------|
| `RATE_LIMIT_EXCEEDED` | 429 | İstek limiti aşıldı; `retry_after_seconds` döner |

---

## 3. Endpoint Kataloğu

### 3.1 Auth

> **Uygulama notu:** Login ucu kodda OAuth2 uyumlu olarak `POST /api/v1/auth/token` (form-urlencoded) şeklinde uygulanmıştır ve yanıt sade `{access_token, token_type}` döner. MFA aktif kullanıcıda yanıt `{mfa_required: true, mfa_token}` olur (bkz. §3.1.1). Aşağıdaki `/login` sözleşmesi hedef/idealize biçimdir.

#### `POST /api/v1/auth/login`
Kullanıcı girişi. Rate limit: 10/dakika per IP.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_at": "2024-01-01T12:15:00Z",
    "csrf_token": "abc123",
    "user": {
      "id": "uuid",
      "username": "string",
      "role": "admin",
      "email": "string|null",
      "title": "string|null",
      "company": "string|null"
    }
  }
}
```
Access token Header'da; refresh token Set-Cookie (httpOnly, Secure, SameSite=Strict).

**Response 401:** `AUTH_INVALID_CREDENTIALS` veya `AUTH_ACCOUNT_LOCKED` (`unlocks_at` alanı ile)

---

#### `POST /api/v1/auth/refresh`
Token yenileme. Cookie'deki refresh token kullanılır.

**Headers:** `X-CSRF-Token: <csrf_token>`

**Response 200:** Login ile aynı yapı (yeni access token + yeni refresh cookie).

**Response 401:** `AUTH_SESSION_REVOKED`

---

#### `POST /api/v1/auth/logout`
Oturumu sonlandırır.

**Headers:** `Authorization: Bearer <token>`, `X-CSRF-Token: <csrf_token>`

**Response 204:** Body yok. Refresh cookie silinir.

---

### 3.1.1 MFA (TOTP — ADR 0007)

#### `POST /api/v1/auth/mfa/verify`
Login'in ikinci faktörü. CSRF muaf (login akışı).
```json
{ "mfa_token": "string", "code": "123456" }
```
**Response 200:** `{ "access_token": "...", "token_type": "bearer" }` + refresh cookie.
**Response 401:** Kod hatalı veya `mfa_token` süresi dolmuş.

#### `POST /api/v1/auth/mfa/setup`  *(auth + CSRF)*
**Response 200:** `{ "secret": "BASE32", "otpauth_uri": "otpauth://totp/..." }`

#### `POST /api/v1/auth/mfa/activate`  *(auth + CSRF)*
`{ "code": "123456" }` → **200** `{ "message": "MFA başarıyla etkinleştirildi." }`

#### `POST /api/v1/auth/mfa/disable`  *(auth + CSRF)*
`{ "code": "123456" }` → **200** `{ "message": "MFA devre dışı bırakıldı." }`

---

### 3.1.2 İlk Kurulum (Bootstrap)

> **Uygulama notu:** 03_DATABASE_SCHEMA.md, ilk admin'in boot-time'da env'den (`ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH`) seed edilmesini öngörür. Uygulanan sürümde bunun yerine, Edge'deki desene paralel bir **UI tabanlı ilk kurulum** akışı vardır: sistemde hiç kullanıcı yokken arayüz "İlk Kurulum" ekranını gösterir ve ilk kullanıcı buradan oluşturulur. Bu uçlar auth ve CSRF muafdır (login öncesi çağrılır) ve yalnızca kullanıcı tablosu boşken çalışır.

#### `GET /api/v1/auth/bootstrap-status`
Sistemde hiç kullanıcı olup olmadığını döner. Frontend açılışta bunu sorgular; `needs_bootstrap` true ise login yerine "İlk Kurulum" ekranı gösterilir.

**Response 200:** `{ "needs_bootstrap": true|false }`

#### `POST /api/v1/auth/bootstrap`
İlk kullanıcıyı oluşturur. **Yalnızca** kullanıcı tablosu boşken çalışır; en az bir kullanıcı varsa kalıcı olarak devre dışıdır.

**Request:**
```json
{ "username": "string", "password": "string", "role": "admin|user" }
```
Şifre `UserCreate` politikasına tabidir (min 12 karakter; büyük/küçük harf, rakam, özel karakter). `role` yalnızca `admin` veya `user` olabilir.

**Response 200:** Oluşturulan kullanıcı (`UserResponse`: `id`, `username`, `role`, ...). Bootstrap yalnızca kullanıcıyı oluşturur; ardından normal login akışına yönlendirilir.

**Response 400:** `BUSINESS_LOGIC_ERROR` — "İlk kullanıcı zaten oluşturulmuş." (tablo boş değil)

---

### 3.2 Kullanıcı Yönetimi

#### `GET /api/v1/users/me`
Mevcut kullanıcının profil bilgileri.

**Response 200:**
```json
{
  "data": {
    "id": "uuid",
    "username": "string",
    "role": "admin|user",
    "email": "string|null",
    "phone": "string|null",
    "title": "string|null",
    "company": "string|null",
    "is_active": true
  }
}
```

---

#### `PATCH /api/v1/users/me`
Kendi profil bilgilerini günceller.

**Request:**
```json
{
  "email": "string|null",
  "phone": "string|null",
  "title": "string|null",
  "company": "string|null",
  "password": "string|null"
}
```
Yalnızca gönderilen alanlar güncellenir. `password` min 12 karakter.

**Response 200:** Güncel user nesnesi.

> **Not:** Profil fotoğrafı yükleme özelliği kaldırılmıştır. Sistemde herhangi bir
> dosya yükleme yüzeyi yoktur; profil avatarı kullanıcının ad/soyad baş harfleriyle
> istemci tarafında üretilir.

---

#### `GET /api/v1/users` *(Admin)*
Tüm kullanıcıları listeler.

**Query params:** `is_active=true|false` (default: tümü), `role=admin|user`

**Response 200:**
```json
{
  "data": [ { ...user nesnesi... } ],
  "meta": { "total": 5 }
}
```

---

#### `POST /api/v1/users` *(Admin)*
Yeni kullanıcı oluşturur.

**Request:**
```json
{
  "username": "string",
  "password": "string",
  "role": "admin|user",
  "title": "string|null",
  "company": "string|null",
  "email": "string|null",
  "phone": "string|null"
}
```

**Response 201:** Yeni user nesnesi.

**Response 409:** `USER_USERNAME_TAKEN`

---

#### `PATCH /api/v1/users/{user_id}` *(Admin)*
Başka kullanıcıyı günceller.

**Request:** Aynı `PATCH /users/me` şeması + `role` alanı (admin değiştirebilir).

**Response 200:** Güncel user nesnesi.

---

#### `DELETE /api/v1/users/{user_id}` *(Admin)*
Kullanıcı siler (hard delete).

**Response 204:** Body yok.

**Response 400:** `USER_CANNOT_DELETE_SELF` veya `USER_LAST_ADMIN`

---

### 3.3 Çalışan (Calisan)

#### `GET /api/v1/calisanlar/{sicil_numarasi}`
Sicil bazlı personel bilgisi döndürür.

**Response 200:**
```json
{
  "data": {
    "sicil_numarasi": "string",
    "ad": "string",
    "soyad": "string",
    "cinsiyet": "K|E|null"
  }
}
```

---

### 3.4 Kıyafet / RFID Yönetimi *(Admin)*

#### `GET /api/v1/kiyafetler`
RFID eşleştirme listesi. Sayfalama ve arama destekli.

**Query params:** `q=string` (ad/soyad/rfid/sicil), `offset=0`, `limit=50`

**Response 200:**
```json
{
  "data": [
    {
      "rfid_tag": "string",
      "sicil_numarasi": "string",
      "ad_soyad": "string"
    }
  ],
  "meta": { "total": 100, "offset": 0, "limit": 50 }
}
```

---

#### `POST /api/v1/kiyafetler`
Yeni RFID eşleştirmesi. Personel yoksa aynı anda oluşturur.

**Request:**
```json
{
  "rfid_tag": "string",
  "sicil_numarasi": "string",
  "ad": "string|null",
  "soyad": "string|null",
  "cinsiyet": "K|E|null"
}
```
`ad` ve `soyad` yeni personel oluşturulacaksa zorunludur.

**Response 201:** `{ "data": { "message": "RFID eşleştirmesi başarılı." } }`

---

#### `PATCH /api/v1/kiyafetler/{rfid_tag}`
Mevcut eşleştirmeyi günceller.

**Request:**
```json
{
  "rfid_tag": "string",
  "sicil_numarasi": "string"
}
```

**Response 200:** `{ "data": { "message": "Güncellendi." } }`

---

#### `DELETE /api/v1/kiyafetler/{rfid_tag}`
Eşleştirmeyi siler.

**Response 204:** Body yok.

**Response 409:** `KIYAFET_HAS_OPEN_RECORDS`

---

### 3.5 İşlem Akışı

#### `POST /api/v1/islem/sepet-simulasyon`
Sepet simülasyonu: RFID listesinden henüz kirli bekleyenlerinde olmayan rastgele en fazla 10 kıyafeti `kirli_kiyafetler`'e ekler. **Yetki: yalnızca `admin`** (`require_admin`); aksi halde 403 döner.

**Response 200:**
```json
{
  "data": {
    "durum": "ok|bos",
    "mesaj": "string",
    "eklenenler": [
      {
        "id": 1,
        "rfid_tag": "string",
        "sicil_numarasi": "string",
        "ad_soyad": "string",
        "cinsiyet": "K|E|null",
        "zaman_damgasi": "ISO8601"
      }
    ],
    "kalan_aday": 15
  }
}
```

---

#### `POST /api/v1/islem/kirli-giris`
Tek RFID tag ile kirli giriş. **Yetki: yalnızca `admin`** (`require_admin`); aksi halde 403 döner.

**Request:**
```json
{
  "rfid_tag": "string"
}
```

**Response 201:** `{ "data": { "id": 1, "rfid_tag": "string", "sicil_numarasi": "string" } }`

**Response 403:** `FORBIDDEN` — admin olmayan kullanıcı

**Response 404:** `ISLEM_RFID_NOT_REGISTERED`

---

#### `POST /api/v1/islem/onayla`
Kirli kaydı onaylar; `temiz_kiyafetler`'e aktarır ve raf atar.

**Request:**
```json
{
  "id": 1
}
```

**Response 200:**
```json
{
  "data": {
    "yeni_id": 5,
    "raf_id": "A11"
  }
}
```

**Response 404:** `ISLEM_KIRLI_NOT_FOUND`

**Response 409:** `ISLEM_SHELF_FULL`

---

#### `POST /api/v1/islem/teslim`
Temiz kaydı teslim eder; `teslim_edilenler`'e aktarır.

**Request:**
```json
{
  "id": 5,
  "sicil_numarasi": "string"
}
```

**Response 200:** `{ "data": { "yeni_id": 20 } }`

**Response 400:** `ISLEM_SICIL_MISMATCH`

**Response 404:** `ISLEM_TEMIZ_NOT_FOUND`

---

### 3.6 Tablolar

#### `GET /api/v1/tablo/{islem_tipi}`
İşlem listesini döndürür. `islem_tipi`: `kirli`, `temiz`, `teslim`, `kiyafet`.

`teslim` ve `kiyafet` yalnızca admin erişebilir.

**Query params:** `q=string`, `offset=0`, `limit=50`

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "rfid_tag": "string",
      "sicil_numarasi": "string",
      "ad_soyad": "string",
      "zaman_damgasi": "ISO8601",
      "raf_id": "A11|null"
    }
  ],
  "meta": { "total": 30, "offset": 0, "limit": 50 }
}
```

---

### 3.7 İstatistikler

#### `GET /api/v1/stats`
Bugünkü özet sayılar.

**Response 200:**
```json
{
  "data": {
    "kirli_bugun": 15,
    "temiz_bugun": 12,
    "teslim_bugun": 10
  }
}
```

---

#### `GET /api/v1/stats/raflar`
Tüm rafların göz bazlı doluluk durumu.

**Response 200:**
```json
{
  "data": {
    "A": {
      "A11": { "count": 2, "capacity": 3 },
      "A12": { "count": 0, "capacity": 3 }
    }
  }
}
```

---

#### `GET /api/v1/stats/raf-detay/{rack_letter}`
Belirli bir rafın (A-H) içindeki kıyafet detayları.

**Response 200:**
```json
{
  "data": {
    "A11": [
      {
        "rfid_tag": "string",
        "sicil_numarasi": "string",
        "ad_soyad": "string",
        "zaman_damgasi": "ISO8601"
      }
    ]
  }
}
```

---

#### `GET /api/v1/stats/gecmis`
Geçmiş günlerin istatistikleri.

**Query params:** `period=weekly|monthly` (default: weekly)

**Response 200:**
```json
{
  "data": {
    "labels": ["01.06", "02.06"],
    "kirli_data": [10, 15],
    "temiz_data": [8, 14],
    "teslim_data": [7, 13]
  }
}
```

---

### 3.8 Audit Log *(Admin)*

#### `GET /api/v1/audit-logs`
Audit log kayıtları. Yalnızca admin.

**Query params:** `username=string`, `action=string`, `limit=100` (max 500), `offset=0`

**Response 200:**
```json
{
  "data": [
    {
      "id": 1,
      "timestamp": "ISO8601",
      "username": "string|null",
      "action": "LOGIN_SUCCESS",
      "detail": "string|null",
      "status": "success|fail"
    }
  ],
  "meta": { "total": 500, "offset": 0, "limit": 100 }
}
```

Note: `ip_hash` alanı API yanıtında döndürülmez (KVKK).

---

### 3.9 Health Check

#### `GET /api/v1/health`
Auth gerektirmez.

**Response 200:**
```json
{
  "data": {
    "status": "healthy|unhealthy",
    "timestamp": "ISO8601",
    "uptime": "2sa 15dk",
    "database": {
      "status": "healthy",
      "latency_ms": 1.5
    }
  }
}
```

---

## 4. Kaldırılan Endpoint'ler (v3'ten v4'e)

Aşağıdaki endpoint'ler **kaldırılmıştır** ve v4'te bulunmamalıdır:

| Endpoint | Gerekçe |
|----------|---------|
| `POST /api/init_mock_data` | Auth gerektirmiyordu; kritik güvenlik açığı |
| `POST /api/token` | `/api/v1/auth/login` ile değiştirildi |
| `PUT /api/users/me` | PATCH ile değiştirildi |
| `PUT /api/users/{user_id}` | PATCH ile değiştirildi |
| `PUT /api/kiyafet/{rfid_tag}` | PATCH ile değiştirildi |
| `GET /api/calisan/{sicil}` | `/api/v1/calisanlar/{sicil}` ile değiştirildi |
