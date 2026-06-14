# LaundroStar — Sistem Topolojisi

**Versiyon:** v3  
**Tarih:** Nisan 2026  
**Repo:** [bgrkurugollu-cpu/camasirhane_v3](https://github.com/bgrkurugollu-cpu/camasirhane_v3)

---

## 1. Genel Bakış

LaundroStar, fabrika/tesis çamaşırhanelerini RFID teknolojisiyle yönetmek için geliştirilmiş bir otomasyon sistemidir. Personel kıyafetlerinin kirli girişinden temiz raf atamasına ve teslimata kadar olan tüm süreci dijital olarak takip eder.

```
┌─────────────────────────────────────────────────────────┐
│                      İstemci (Tarayıcı)                 │
│          Vanilla JS + Tailwind CSS + Chart.js           │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS :443
┌─────────────────────▼───────────────────────────────────┐
│                  Nginx (Reverse Proxy)                  │
│          HTTP :80 → HTTPS :443  |  SSL Termination      │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP :8086 (internal)
┌─────────────────────▼───────────────────────────────────┐
│              FastAPI + Uvicorn (Python 3.11)            │
│         JWT Auth · Rate Limit · Audit Log · REST API    │
└─────────────────────┬───────────────────────────────────┘
                      │ SQLAlchemy (psycopg2)
┌─────────────────────▼───────────────────────────────────┐
│              PostgreSQL 16 (Alpine)                     │
│     calisanlar · kiyafetler · kirli/temiz/teslim        │
│     users · audit_logs                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Container Mimarisi

Sistem 3 Docker container'dan oluşur ve `docker compose` ile yönetilir.

| Container | Image | Port | Görev |
|---|---|---|---|
| `laundrostar_nginx` | nginx:1.25-alpine | 80, 443 | Reverse proxy, SSL termination, HTTP→HTTPS yönlendirme |
| `laundrostar_web` | python:3.11-slim (build) | 8086 (iç) | FastAPI uygulama sunucusu |
| `laundrostar_db` | postgres:16-alpine | 5432 (iç) | İlişkisel veritabanı |

### Başlatma Sırası

```
laundrostar_db  →  (healthcheck: pg_isready)
      ↓
laundrostar_web →  (depends_on: db healthy)
      ↓
laundrostar_nginx → (depends_on: web)
```

### Volume'lar

| Volume | Bağlandığı Yer | İçerik |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Kalıcı veritabanı dosyaları |
| `./app` → `/code/app` | Web container | Canlı uygulama kodu (hot-reload) |
| `./nginx/nginx.conf` | `/etc/nginx/conf.d/default.conf` | Nginx yapılandırması |
| `./nginx/certs` | `/etc/nginx/certs` | SSL sertifika ve anahtar |

---

## 3. Uygulama Katmanı (FastAPI)

### 3.1 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Web Framework | FastAPI ≥ 0.103 |
| ASGI Sunucu | Uvicorn ≥ 0.23 |
| ORM | SQLAlchemy ≥ 2.0 |
| DB Sürücüsü | psycopg2-binary |
| Şema Doğrulama | Pydantic v2 |
| Kimlik Doğrulama | JWT (python-jose) + OAuth2PasswordBearer (RS256) |
| Şifre Hashleme | bcrypt (passlib) |
| Rate Limiting | slowapi (IP bazlı) |
| Frontend | Vanilla JS + Tailwind CSS (CDN) + Chart.js |

### 3.2 API Endpoint Haritası

> **Önek:** Tüm uygulama uçları `/api/v1` öneki altındadır (ör. `/api/v1/auth/token`). Aşağıdaki tablolar bu öneki taşır. (Tek istisna: `/api/health` — versiyonsuz health probe.)

#### Auth & MFA
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| POST | `/api/v1/auth/token` | Herkese açık | Login (1. faktör). MFA aktifse `{mfa_required, mfa_token}` döner (10 istek/dk) |
| POST | `/api/v1/auth/mfa/verify` | mfa_token | Login 2. faktör — TOTP kodu doğrula, oturum aç (ADR 0007) |
| POST | `/api/v1/auth/mfa/setup` | user/admin | MFA kaydı başlat (secret + `otpauth://` URI) |
| POST | `/api/v1/auth/mfa/activate` | user/admin | TOTP kodu ile MFA'yı etkinleştir |
| POST | `/api/v1/auth/mfa/disable` | user/admin | Geçerli kod ile MFA'yı kapat |
| POST | `/api/v1/auth/refresh` | refresh cookie | Yeni access token |
| POST | `/api/v1/auth/logout` | — | Refresh cookie temizle |
| GET | `/api/v1/users/me` | user/admin | Kendi profil bilgisi |
| PUT | `/api/v1/users/me` | user/admin | Profil güncelleme |
| POST | `/api/v1/users/me/photo` | user/admin | Profil fotoğrafı yükleme (PNG; magic-byte + boyut doğrulamalı, bkz. §7 Dosya Yükleme Güvenliği) |

#### Kullanıcı Yönetimi (Admin)
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/v1/users` | admin | Tüm kullanıcıları listele |
| POST | `/api/v1/users` | admin | Yeni kullanıcı oluştur |
| PUT | `/api/v1/users/{id}` | admin | Kullanıcı güncelle |
| DELETE | `/api/v1/users/{id}` | admin | Kullanıcı sil |

#### Çalışan & RFID Eşleştirme
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/v1/calisan/{sicil}` | user/admin | Sicil numarasına göre personel getir |
| POST | `/api/v1/kiyafet` | admin | Yeni RFID–sicil eşleştirmesi ekle |
| PUT | `/api/v1/kiyafet/{rfid}` | admin | RFID eşleştirmesini güncelle |
| DELETE | `/api/v1/kiyafet/{rfid}` | admin | RFID eşleştirmesini sil |

#### İş Akışı / İşlemler
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| POST | `/api/v1/islem/rfid-oku` | user/admin | Kirli sepet simülasyonu (rastgele 10 kıyafet ekler) |
| POST | `/api/v1/islem` | user/admin | Manuel kirli / temiz / teslim kaydı oluştur (60 istek/dk) |
| POST | `/api/v1/islem/onayla` | user/admin | Kirli kıyafeti "temiz" olarak işaretle, raf ata |
| POST | `/api/v1/islem/teslim` | user/admin | Temiz kıyafeti personele teslim et |

#### İstatistik & Raporlama
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/v1/stats` | user/admin | Günlük kirli/temiz/teslim sayıları |
| GET | `/api/v1/stats/raflar` | user/admin | Tüm rafların doluluk durumu |
| GET | `/api/v1/stats/raf-detay/{harf}` | user/admin | Belirli raftaki kıyafet detayları |
| GET | `/api/v1/stats/history` | user/admin | Haftalık/aylık geçmiş grafik verisi |

#### Tablolar
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/v1/tablo/kirli` | user/admin | Onay bekleyen kirli kıyafetler (son 50) |
| GET | `/api/v1/tablo/temiz` | user/admin | Rafta bekleyen temiz kıyafetler (son 50) |
| GET | `/api/v1/tablo/teslim` | admin | Tüm teslim geçmişi (son 50) |
| GET | `/api/v1/tablo/kiyafet` | admin | RFID eşleştirme tablosu (server-side arama + sayfalama) |

#### Denetim
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/v1/audit-logs` | admin | Sistem audit logları (filtreli: `username`, `action`, `limit`) |

> Not: Auth gerektirmeyen `init_mock_data` benzeri uçlar **bilinçli olarak yoktur** (güvenlik). Test verisi `seed_1000.py` scripti ile yüklenir.

---

## 4. Veritabanı Şeması

```
┌──────────────┐         ┌──────────────────┐
│    users     │         │    audit_logs    │
│──────────────│         │──────────────────│
│ id (PK)      │         │ id (PK)          │
│ username     │         │ timestamp        │
│ hashed_pw    │         │ username         │
│ role         │         │ action           │
│ email        │         │ detail           │
│ phone        │         │ ip_address       │
│ title        │         │ status           │
│ company      │         └──────────────────┘
│ profile_photo│
└──────────────┘

┌──────────────────┐       ┌──────────────────┐
│    calisanlar    │       │    kiyafetler    │
│──────────────────│       │──────────────────│
│ sicil_numarasi   │◄──────│ rfid_tag (PK)    │
│ (PK)             │  FK   │ sicil_numarasi   │
│ ad               │       └──────────────────┘
│ soyad            │
│ cinsiyet (K/E)   │
└────────┬─────────┘
         │ FK (sicil_numarasi)
    ┌────┴──────────────────────────────────────────┐
    │                                               │
┌───▼──────────────┐  ┌─────────────────┐  ┌───────▼─────────┐
│  kirli_kiyafetler│  │ temiz_kiyafetler│  │ teslim_edilenler│
│──────────────────│  │─────────────────│  │─────────────────│
│ islem_id (PK)    │  │ islem_id (PK)   │  │ islem_id (PK)   │
│ rfid_tag         │  │ rfid_tag        │  │ rfid_tag        │
│ sicil_numarasi   │  │ sicil_numarasi  │  │ sicil_numarasi  │
│ zaman_damgasi    │  │ zaman_damgasi   │  │ zaman_damgasi   │
└──────────────────┘  │ raf_id          │  │ raf_id          │
                      └─────────────────┘  └─────────────────┘
```

### Veritabanı İndeksleri

| Tablo | Kolon(lar) | Tür |
|---|---|---|
| `calisanlar` | `sicil_numarasi` | PRIMARY KEY + btree |
| `calisanlar` | `ad` | btree |
| `calisanlar` | `soyad` | btree |
| `calisanlar` | `(ad, soyad)` | btree (bileşik, arama hızı) |
| `kiyafetler` | `rfid_tag` | PRIMARY KEY + btree |
| `kiyafetler` | `sicil_numarasi` | btree (FK join hızı) |

---

## 5. Raf Sistemi

```
Raf Harfleri: A B C D E F G H  (8 raf)
Kat Sayısı  : 1–7              (7 kat)
Bölme Sayısı: 1–5              (5 bölme/kat)

Kapasite:
  Kat 1–6 → 3 kıyafet/bölme
  Kat 7   → 1 kıyafet/bölme (en üst, küçük)

Raf başına kapasite = (6 × 5 × 3) + (1 × 5 × 1) = 95
Toplam kapasite     = 8 × 95 = 760

Cinsiyet Ayrımı:
  Kadın  → Yalnızca E rafı  (95 kıyafet)
  Erkek  → A,B,C,D,F,G,H   (665 kıyafet)

Raf ID formatı: {Harf}{Kat}{Bölme}  →  örn: A11, E73, H65
```

### Raf Atama Algoritması

```
1. Cinsiyete göre raf harfi havuzu belirlenir
2. Harf → Kat → Bölme sırasıyla taranır
3. Mevcut doluluk < kapasite olan ilk bölme atanır
4. Tüm bölmeler doluysa HTTP 400 döner
```

---

## 6. İş Akışı (Kıyafet Yaşam Döngüsü)

```
[Personel kıyafetini getirir]
           │
           ▼
   ┌───────────────┐
   │ RFID Okutma  │  → rfid_tag okunur
   │ (Kirli Giriş)│  → kirli_kiyafetler tablosuna eklenir
   └───────┬───────┘
           │
           ▼
   ┌───────────────┐
   │ Onay (Admin) │  → kirli_kiyafetler'den silinir
   │              │  → Cinsiyete göre raf atanır
   │              │  → temiz_kiyafetler tablosuna eklenir
   └───────┬───────┘
           │
           ▼
   ┌───────────────┐
   │ Teslim       │  → temiz_kiyafetler'den silinir
   │              │  → Sicil eşleşmesi doğrulanır
   │              │  → teslim_edilenler tablosuna eklenir
   └───────────────┘
```

---

## 7. Güvenlik

| Mekanizma | Detay |
|---|---|
| Kimlik Doğrulama | JWT **RS256** (asimetrik, private/public key), `Authorization: Bearer <token>` (bkz. ADR 0001) |
| Access Token Süresi | 15 dk (`ACCESS_TOKEN_EXPIRE_MINUTES`, `.env`) |
| Refresh Token Süresi | 7 gün, httpOnly+Secure cookie (`REFRESH_TOKEN_EXPIRE_DAYS`) |
| Admin MFA | **TOTP (RFC 6238) uygulanmıştır** — `pyotp`. `/auth/mfa/*` uçları; ADR 0007. `ADMIN_MFA_REQUIRED` ile zorunlu kayıt politikası açılır. |
| Şifre Hashleme | bcrypt (passlib); min 12 karakter politika doğrulaması (Pydantic) |
| Hesap Kilitleme | 5 hatalı denemede 15 dk kilit |
| CSRF | Double Submit Cookie (`CSRFMiddleware`); auth/login ve `mfa/verify` muaf (bkz. ADR 0005) |
| Rate Limiting | `/api/v1/auth/token`: 10 istek/dk · `/api/v1/islem*`: 60 istek/dk (IP bazlı, slowapi) |
| Yetkilendirme | Role-based: `admin` ve `user` |
| SSL/TLS | TLS 1.2/1.3, Nginx'te terminate edilir |
| Audit Log | Tüm giriş, çıkış ve işlem olayları `audit_logs` tablosuna yazılır (PostgreSQL RULE ile append-only). Log aggregation hedefi: bkz. Bölüm 13. |
| Proxy Desteği | `X-Forwarded-For` başlığından gerçek IP alınır |
| Dosya Yükleme | Profil fotoğrafı yüklemede çok katmanlı içerik doğrulaması uygulanır (bkz. §7.1). |
| Swagger/Docs | Üretimde kapalı: `DOCS_URL`/`REDOC_URL` env'leri set edilmedikçe `/docs` ve `/redoc` devre dışıdır (`docs_url=None`). |

### 7.1 Dosya Yükleme Güvenliği (Profil Fotoğrafı)

`POST /api/v1/users/me/photo` ucu tek dosya yükleme noktasıdır. Yalnızca MIME tipine güvenmek yetersizdir; polyglot saldırıları (PNG başlığı taşıyan kötücül içerik) bu denetimi atlatabilir. Bu nedenle yüklenen her dosya aşağıdaki katmanlı denetimden geçer (`app/modules/kullanici/service.py`):

| # | Denetim | Kural | Başarısızlık davranışı |
|---|---|---|---|
| 1 | MIME tipi | `Content-Type == image/png` | Reddet → `BusinessLogicException` (HTTP 400) |
| 2 | Boyut limiti | `len(contents) ≤ 2 MB` (boş dosya da reddedilir) | Reddet → `BusinessLogicException` (HTTP 400) |
| 3 | **Magic byte (imza)** | İlk 8 byte = `89 50 4E 47 0D 0A 1A 0A` (PNG signature) | Reddet → `BusinessLogicException` (HTTP 400) |
| 4 | Güvenli yazım | Dosya adı sunucuda üretilir (`avatar_{id}_{uuid}.png`); kullanıcı girdisi dosya yoluna karışmaz (path traversal yok) | — |

**Tarama başarısız olduğunda politika:** İstek **reddedilir** (karantina/diske yazma yapılmaz) ve olay `PHOTO_UPLOAD_REJECTED` action koduyla audit log'a (`status="failure"`) yazılır. Başarılı yüklemeler `PHOTO_UPLOAD` koduyla loglanır. Reddedilen yüklemelerin tekrarı, §13'teki "kritik log" alerting kategorisi üzerinden yöneticiye sinyal verir.

> **Not (gelecek sertleştirme):** Antivirüs taraması gerektiren genişletilmiş yükleme senaryolarında (ör. doküman eki) ClamAV/`clamd` sidecar entegrasyonu planlanmıştır; Faz 1'in tek küçük PNG yükleme yüzeyi için magic-byte + boyut + sunucu-üretimli ad yeterli kabul edilmiştir.

---

## 8. Frontend

| Bileşen | Teknoloji | Açıklama |
|---|---|---|
| UI Framework | Tailwind CSS (CDN) | Utility-first CSS |
| JavaScript | Vanilla ES6+ | Harici framework yok |
| Grafikler | Chart.js (CDN) | İstatistik grafikleri |
| QR Okuma | html5-qrcode | Kamera ile RFID/QR okuma |
| QR Üretme | QRious | Barkod önizleme modalında QR oluşturma |
| PDF | jsPDF | Barkod PDF çıktısı |
| State | memory-only (`AppState`) | Access token **yalnızca bellekte** tutulur; `localStorage`'a yazılmaz. Refresh token httpOnly+Secure cookie'dedir (ADR 0001). |
| Auth Akışı | Token yoksa login modal gösterilir; tüm API istekleri `fetchWithAuth()` ile yapılır. 401'de `/auth/refresh` üzerinden sessiz token yenileme (Silent Refresh) denenir. |

---

## 9. Yapılandırma (`.env`)

> ⚠️ **Not:** JWT imzalama **RS256** (asimetrik) ile yapılır; simetrik `SECRET_KEY`/`HS256` **kullanılmaz**. Anahtarlar PEM dosyalarından okunur (bkz. ADR 0001).

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy bağlantı dizesi (zorunlu) | — |
| `DB_POOL_SIZE` | Kalıcı bağlantı havuzu boyutu | `10` |
| `DB_MAX_OVERFLOW` | Havuz dolduğunda açılabilecek ek bağlantı sayısı | `20` |
| `DB_POOL_TIMEOUT` | Havuzdan bağlantı beklerken zaman aşımı (sn) | `30` |
| `DB_POOL_RECYCLE` | Bağlantının geri dönüştürülme süresi (sn) | `1800` |
| `PRIVATE_KEY_PATH` | RS256 private key (PEM) yolu | `certs/private_key.pem` |
| `PUBLIC_KEY_PATH` | RS256 public key (PEM) yolu | `certs/public_key.pem` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token ömrü (dk) | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token ömrü (gün) | `7` |
| `CORS_ORIGINS` | İzinli origin listesi (virgülle) — `*` yasak | `http://localhost` |
| `DOCS_URL` / `REDOC_URL` | Swagger/ReDoc yolu; set edilmezse kapalı | (kapalı) |
| `MFA_ISSUER` | TOTP issuer adı (authenticator'da görünür) | `LaundroStar` |
| `MFA_TOKEN_EXPIRE_MINUTES` | MFA ara token ömrü (dk) | `5` |
| `ADMIN_MFA_REQUIRED` | Admin'ler için MFA kayıt zorunluluğu uyarısı | `false` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | PostgreSQL kimlik bilgileri | — |
| `TEST_DATABASE_URL` | Testlerde gerçek Postgres (opsiyonel; yoksa sqlite) | (sqlite) |
| `TZ` | Zaman dilimi | `Europe/Istanbul` |

---

## 10. Dizin Yapısı

```
laundrostar/
├── docker-compose.yml       # Servis tanımları
├── Dockerfile               # Web container build tarifi
├── requirements.txt         # Python bağımlılıkları
├── seed_1000.py             # 1000 kişilik test verisi scripti
├── .env                     # Ortam değişkenleri (git'e dahil değil)
├── nginx/
│   ├── nginx.conf           # Reverse proxy yapılandırması
│   └── certs/
│       ├── cert.pem         # SSL sertifikası
│       └── key.pem          # SSL özel anahtarı
├── app/
│   ├── main.py              # FastAPI giriş noktası: app factory, middleware (CORS/CSRF/SecurityHeaders),
│   │                        #   rate limiter ve router kayıtları. Endpoint TANIMLARI burada DEĞİL,
│   │                        #   modules/*/router.py içindedir.
│   ├── models.py            # SQLAlchemy ORM modelleri
│   ├── schemas.py           # Pydantic istek/yanıt şemaları
│   ├── database.py          # DB bağlantısı, connection pool ve session yönetimi
│   ├── security.py          # JWT (RS256), bcrypt, OAuth2 ve TOTP/MFA yardımcıları
│   ├── exceptions.py        # AppException hiyerarşisi (standart hata envelope)
│   ├── logger.py            # structlog JSON loglama + kritik log helper'ı
│   ├── utils.py             # IP alma, audit log yazma yardımcıları
│   ├── modules/             # Modüler monolith — her modül: router.py / service.py / repository.py
│   │   ├── auth/            # Login, MFA, refresh, logout
│   │   ├── kullanici/       # Kullanıcı yönetimi + profil fotoğrafı yükleme
│   │   ├── islem/           # İşlem akışı, istatistik, tablolar + shelf_service.py (raf atama)
│   │   ├── calisan/         # Personel sorgulama
│   │   ├── kiyafet/         # RFID demirbaş yönetimi
│   │   └── audit/           # Denetim kaydı sorgulama
│   └── static/
│       ├── index.html       # Tek sayfa uygulama (SPA)
│       ├── app.js           # Tüm frontend iş mantığı
│       ├── style.css        # Özel stiller
│       ├── logo.png         # Uygulama logosu
│       └── avatars/         # Profil fotoğrafları
└── docs/
    ├── topoloji.md          # Bu doküman
    ├── adr/                 # Architecture Decision Records (0001–0008)
    └── ...
```

---

## 11. API Katmanlama (Internal / Private / Public)

Mimari Gate önerisi doğrultusunda uçlar güvenlik sınırlarına göre üç katmana ayrılır:

| Katman | Tanım | Erişim sınırı | Örnek uçlar |
|---|---|---|---|
| **Public** | Kimlik doğrulama gerektirmeyen, dışarıya açık | Nginx üzerinden, rate-limited | `POST /api/v1/auth/token`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/mfa/verify`, `GET /api/health` |
| **Private** | Geçerli JWT (user/admin) gerektiren uygulama uçları | Yalnızca authenticated SPA | `/api/v1/islem*`, `/api/v1/stats*`, `/api/v1/tablo/{kirli,temiz}`, `/api/v1/users/me*`, `/api/v1/calisan/*`, `/api/v1/auth/mfa/{setup,activate,disable}` |
| **Internal/Admin** | Yalnızca `admin` rolü; yönetim ve denetim | `require_admin` / servis-içi rol kontrolü | `/api/v1/users` (CRUD), `/api/v1/kiyafet*`, `/api/v1/tablo/{teslim,kiyafet}`, `/api/v1/audit-logs` |

Tüm katmanlar aynı modüler monolith içinde sunulur; sınır, kod seviyesinde dependency (`get_current_user` / rol kontrolü) ve Nginx seviyesinde TLS + rate limit ile uygulanır. İleride dışarıya entegrasyon API'si açılırsa, Public katman ayrı bir Nginx `location` ve API key/gateway ile izole edilir.

---

## 12. Beklenen Yük ve Kapasite

| Boyut | Tahmin (Faz 1 hedef tesis) |
|---|---|
| Aktif personel | ~1.000 (bkz. `seed_1000.py`) |
| Eş zamanlı operatör (kiosk) | 5–15 |
| Günlük RFID/işlem hacmi | ~2.000–5.000 işlem (kirli+temiz+teslim) |
| Pik istek hızı | < 60 istek/dk/uç (rate limit ile sınırlanmış) |
| Raf kapasitesi | 760 kıyafet (8 raf × 95) — bkz. ADR 0004 |
| Veri büyümesi | Audit log append-only; yıllık ~1–2M kayıt mertebesi |

Bu yük profili tek `web` container + tek PostgreSQL örneği ile rahatça karşılanır (ADR 0006). Yatay ölçekleme gerekirse: stateless JWT + Double Submit CSRF sayesinde `web` çoğaltılabilir; PostgreSQL read-replica eklenebilir.

---

## 13. Loglama ve Log Aggregation

- **Uygulama logları:** `structlog` ile JSON formatında stdout'a yazılır (`app/logger.py`).
- **Audit log:** Kritik işlemler `audit_logs` tablosuna (PostgreSQL `RULE` ile append-only) yazılır.
- **Aggregation hedefi:** Container stdout JSON logları, deployment ortamında bir log shipper (Filebeat/Fluent Bit) aracılığıyla **OpenSearch/Elasticsearch (ELK)** kümesine gönderilir. Tercih edilen hedef OpenSearch'tür; bulut dağıtımında CloudWatch Logs alternatiftir. Bu, gözlemlenebilirlik ve uzun süreli denetim saklama için standart hattır.

### Log Kategorileri ve Alerting

Loglar üç anlamsal kategoriye ayrılır. Kategori, JSON log satırındaki `category` alanı ile işaretlenir ve aggregation katmanında alerting kuralları bu alana göre kurulur.

| Kategori | Üretim noktası | İçerik | Alerting |
|---|---|---|---|
| `app` | `logger.info/warning(...)` | Normal istek/yanıt akışı, beklenen hatalar (4xx) | Yok (sadece arşiv/analiz) |
| `audit` | `audit_logs` tablosu | Login/logout, kullanıcı/RFID CRUD, işlem onay/teslim, foto yükleme | Eşik bazlı (ör. tekrarlı `*_REJECTED`) |
| **`critical`** | `logger.critical(...)` → `log_critical()` helper | DB erişilemezliği, beklenmeyen 5xx, güvenlik ihlali şüphesi (tekrarlı hesap kilidi, CSRF reddi seli, reddedilen dosya yükleme tekrarı) | **Anında** — OpenSearch Alerting / Prometheus Alertmanager üzerinden e-posta/Slack/webhook |

**Kritik log tanımı:** Aşağıdaki olaylar `critical` kategorisinde üretilir ve operasyonel müdahale gerektirir:
- Veritabanı bağlantı havuzunun tükenmesi veya `OperationalError` (DB çöküşü)
- Aynı hesapta kısa sürede tekrarlayan kilitlenme (`ACCOUNT_LOCKED`) — brute-force şüphesi
- `PHOTO_UPLOAD_REJECTED` olaylarının kısa pencerede tekrarı — polyglot/malware deneme şüphesi
- Yakalanmayan istisna kaynaklı HTTP 5xx

Alerting entegrasyonu deployment ortamında kurulur (OpenSearch Alerting monitor'ü veya Alertmanager kuralı); uygulama yalnızca `category="critical"` etiketli JSON satırını üretmekten sorumludur. Bu sayede alerting altyapısı kodtan bağımsız değiştirilebilir.
