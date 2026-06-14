# Geliştirici Dokümantasyonu (Developer Guide)

Bu doküman, LaundroStar projesinin teknik mimarisini ve geliştirme standartlarını açıklar.

---

## Mimari Genel Bakış

Sistem üç Docker servisinden oluşur:

| Servis | İmaj | Görev |
|---|---|---|
| `db` | postgres:16-alpine | Kalıcı veri deposu |
| `web` | Dockerfile (Python 3.11) | FastAPI uygulaması (uvicorn) |
| `nginx` | nginx:alpine | Reverse proxy, TLS sonlandırma |

Nginx dışarıdan gelen tüm HTTP/HTTPS isteklerini karşılar ve `web` servisine iletir. `web` servisi doğrudan dışarıya açık değildir. Veriler `postgres_data` Docker volume'una yazılır.

---

## Kod Katmanları

### `app/database.py`
PostgreSQL bağlantısını `DATABASE_URL` ortam değişkeninden okur. `SessionLocal` ile her endpoint çağrısı için izole bir veritabanı oturumu açar; `finally` bloğuyla kapatır. `pool_pre_ping=True` sayesinde bağlantı kopuklarını otomatik algılar.

**Connection pool:** Havuz parametreleri env'den okunur ve kod içinde sabit değildir (bkz. `topoloji.md §9`):

| Env | Anlam | Varsayılan |
|---|---|---|
| `DB_POOL_SIZE` | Kalıcı bağlantı sayısı | `10` |
| `DB_MAX_OVERFLOW` | Havuz dolunca açılabilecek ek bağlantı | `20` |
| `DB_POOL_TIMEOUT` | Bağlantı bekleme zaman aşımı (sn) | `30` |
| `DB_POOL_RECYCLE` | Bağlantı geri dönüşüm süresi (sn) | `1800` |

Pool argümanları yalnızca gerçek havuzlu sürücülerde (PostgreSQL) uygulanır; `sqlite` (test fallback) bunları desteklemediği için atlanır. Havuz tükenmesi (`TimeoutError`/`OperationalError`) `critical` log kategorisinde raporlanır (`topoloji.md §13`).

### `app/exceptions.py`
Projenin tüm hata (exception) yapısını yönetir. `AppException` isimli temel bir sınıf üzerinden `{"error": {"code": "...", "message": "..."}}` formatında standartlaştırılmış hatalar üretilir.

### `app/modules/`
Tüm özellikler Service ve Repository katmanlarına bölünmüştür:
- **Repository Katmanı:** Veritabanı sorguları (SQLAlchemy).
- **Service Katmanı:** İş mantığı (Business logic).
- **Router Katmanı:** HTTP İstek / Yanıt karşılama.
(Örn: `auth`, `islem`, `kullanici`, `kiyafet`, `calisan`, `audit` modülleri bu yapıda kurgulanmıştır.)

### `app/models.py`
SQLAlchemy ORM tablo tanımları:

| Model | Tablo | Açıklama |
|---|---|---|
| `Calisan` | `calisanlar` | Personel kaydı (sicil, ad, rfid, cinsiyet) |
| `Kiyafet` | `kiyafetler` | RFID demirbaş kaydı |
| `Kirli_Kiyafet` | `kirli_kiyafetler` | Çamaşırhanede bekleyen kirli kıyafetler |
| `Temiz_Kiyafet` | `temiz_kiyafetler` | Temizlendi işlemi tamamlananlar |
| `Teslim_Edilen` | `teslim_edilenler` | Teslim için bekleyenler |
| `AuditLog` | `audit_logs` | Tüm kritik işlemlerin denetim kaydı |
| `User` | `users` | Sistem kullanıcıları (admin/user rolleri) |

Tüm zaman sütunları `DateTime(timezone=True)` ile tanımlanmıştır. `raf_id` alanı `String` tipindedir (örn: `"A37"`).

### `app/schemas.py`
Pydantic ile istek (Request) ve yanıt (Response) modellerini tanımlar. Her endpoint gelen veriyi bu şemalar üzerinden doğrular.

### `app/security.py`
- Şifreler `passlib[bcrypt]` ile hashlenir.
- JWT tokenlar `python-jose` ile **RS256** (asimetrik) algoritmasıyla oluşturulur ve doğrulanır (bkz. ADR 0001). HS256/`SECRET_KEY` **kullanılmaz**.
- Anahtarlar `PRIVATE_KEY_PATH` / `PUBLIC_KEY_PATH` PEM dosyalarından, token süreleri `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` env'lerinden okunur.
- `get_current_user` dependency'si tüm korumalı endpointlerde kullanılır.
- `require_admin` dependency'si ve servis katmanındaki rol kontrolleri (`current_user.role != "admin"`) ile RBAC uygulanır.
- **MFA (TOTP):** `pyotp` ile `generate_mfa_secret`, `mfa_provisioning_uri`, `verify_mfa_code` ve kısa ömürlü `create_mfa_token`/`decode_mfa_token` yardımcıları (ADR 0007).

### `app/main.py`
Uygulamanın çekirdeği. Temel sabitler ve fonksiyonlar:

```python
RACK_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
RACK_FLOORS = 7
RACK_COMPARTMENTS = 5

def get_compartment_capacity(floor: int) -> int:
    return 1 if floor == 7 else 3

def assign_shelf(db, cinsiyet=None) -> str:
    # Cinsiyete göre raf seçimi:
    # Kadın → yalnızca E rafı
    # Erkek → A-D ve F-H rafları
    # Boş/kısmi gözler kapasite dolum sırasına göre doldurulur
```

---

## API Uç Noktaları (Özet)

> Tüm uçlar `/api/v1` öneki altındadır. Tam liste için bkz. `topoloji.md` §3.2. Endpoint adları kod (`app/modules/*/router.py`) ile birebir tutulmuştur.

### Kimlik Doğrulama & MFA
| Metod | Yol | Açıklama | Rate Limit |
|---|---|---|---|
| POST | `/api/v1/auth/token` | Giriş (1. faktör); MFA aktifse `{mfa_required, mfa_token}` | 10/dakika |
| POST | `/api/v1/auth/mfa/verify` | Login 2. faktör (TOTP) → access token | — |
| POST | `/api/v1/auth/mfa/setup` · `/activate` · `/disable` | MFA kayıt/aktivasyon/iptal (ADR 0007) | — |
| POST | `/api/v1/auth/refresh` · `/logout` | Token yenileme / çıkış | — |

> Self-servis kayıt (`/register`) **yoktur**; kullanıcılar yalnızca admin tarafından `POST /api/v1/users` ile oluşturulur.

### İşlem (Kıyafet Döngüsü)
| Metod | Yol | Açıklama | Rate Limit |
|---|---|---|---|
| POST | `/api/v1/islem` | Tek uç; gövdedeki `islem_tipi` ∈ {`kirli`,`temiz`,`teslim`} | 60/dakika |
| POST | `/api/v1/islem/onayla` | Kirli kaydı temizlendi yap, raf ata (yanıt `raf_id` içerir) | 60/dakika |
| POST | `/api/v1/islem/teslim` | Temiz kaydı personele teslim et (sicil doğrulamalı) | 60/dakika |
| POST | `/api/v1/islem/rfid-oku` | Rastgele ≤10 kıyafet için kirli sepet simülasyonu | — |

### Tablo Listeleme
| Metod | Yol | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/v1/tablo/kirli` | user/admin | Kirli kıyafetler (ad soyad JOIN) |
| GET | `/api/v1/tablo/temiz` | user/admin | Temiz kıyafetler (ad soyad JOIN) |
| GET | `/api/v1/tablo/teslim` | admin | Teslim geçmişi |
| GET | `/api/v1/tablo/kiyafet` | admin | RFID eşleştirme listesi (arama + sayfalama) |

### İstatistik ve Raf
| Metod | Yol | Açıklama |
|---|---|---|
| GET | `/api/v1/stats` | Günlük kirli/temiz/teslim sayıları |
| GET | `/api/v1/stats/raflar` | Tüm rafların doluluk özeti |
| GET | `/api/v1/stats/raf-detay/{rack_letter}` | Belirli bir rafın tüm gözlerinin detayı |
| GET | `/api/v1/stats/history?period=weekly\|monthly` | Geçmiş grafik verisi |

### Yönetim (Admin)
| Metod | Yol | Açıklama |
|---|---|---|
| GET/POST | `/api/v1/users` | Kullanıcı listesi / ekleme |
| PUT/DELETE | `/api/v1/users/{user_id}` | Kullanıcı güncelleme / silme |
| GET | `/api/v1/calisan/{sicil_numarasi}` | Personel getir |
| POST/PUT/DELETE | `/api/v1/kiyafet[/{rfid}]` | RFID demirbaş ekle / güncelle / sil |
| GET | `/api/v1/audit-logs` | Denetim kaydı (filtreli) |

---

## Raf Kimlik Formatı

Raf ID'si `{Harf}{Kat}{Kompartıman}` formatındadır:
- `A` = Raf harfi (A–H)
- `3` = Kat (1–7)
- `7` = Kompartıman (1–5)
- Örnek: `"A37"` = A rafı, 3. kat, 7. kompartıman *(aslında 5 kompartıman var, bu format birleşik string)*

Gerçek format: `f"{harf}{kat}{kompartiman}"` — örn. `"A31"` (A rafı, 3. kat, 1. kompartıman).

---

## Güvenlik Katmanları (Faz 2 Vibecoding Standartları)

- **XSS Koruması:** `innerHTML` kullanımları tamamen yasaklanmış ve sıfırlanmıştır. Tüm dinamik içerikler DOM Helper (`document.createElement` / `textContent`) mimarisiyle oluşturulmaktadır.
- **Token Güvenliği:** Token'ların `localStorage` üzerinde saklanması iptal edilmiştir. Sistem memory-only state (`AppState`) ve Silent Token Refresh mekanizması ile çalışmaktadır.
- **JWT RS256:** HMAC (HS256) yerine Asimetrik RS256 (Private/Public Key) şifrelemesi kullanılmaktadır (ADR 0001).
- **Admin MFA (TOTP):** Admin/kullanıcı hesapları için `pyotp` tabanlı iki faktörlü doğrulama. Login 1. faktör (şifre) sonrası MFA aktifse `/auth/mfa/verify` ile TOTP istenir (ADR 0007).
- **CSRF ve Güvenlik Başlıkları:** `Double Submit Cookie` mantığı ile CSRF koruması aktiftir; `auth/token`, `auth/refresh`, `auth/logout`, `auth/mfa/verify` muaftır. `SecurityHeadersMiddleware` ile CSP, X-Frame-Options gibi başlıklar zorunlu kılınmıştır.
- **Rate Limiting:** `slowapi` ile IP başına istek sınırı (`/api/v1/auth/token`: 10/dk, `/api/v1/islem*`: 60/dk).
- **Hesap Kilitleme:** 5 hatalı şifre denemesinde hesap 15 dakika boyunca kilitlenir.
- **CORS:** `allow_origins` `CORS_ORIGINS` env'inden okunur; wildcard `*` kullanılmaz.
- **Dosya Yükleme Güvenliği:** Tek yükleme noktası olan profil fotoğrafı (`POST /api/v1/users/me/photo`) çok katmanlı doğrulamadan geçer (`app/modules/kullanici/service.py`): (1) MIME tipi `image/png`, (2) boyut ≤ 2MB (boş dosya reddedilir), (3) **magic byte / PNG imzası** (`\x89PNG\r\n\x1a\n`) — yalnızca MIME tipine güvenmek polyglot saldırılarına açıktır, (4) dosya adı sunucuda üretilir (`avatar_{id}_{uuid}.png`) → path traversal engellenir. Denetimlerden herhangi biri başarısız olursa dosya **diske yazılmaz**, istek reddedilir ve olay `PHOTO_UPLOAD_REJECTED` koduyla audit log'a yazılır; başarılı yükleme `PHOTO_UPLOAD` ile loglanır. Tarama politikası ve gelecekteki ClamAV genişletmesi için bkz. `topoloji.md §7.1`.
- **Nginx & Docker:** Uygulamanın doğrudan internet erişimi engellenir. Dockerfile non-root (`appuser`) profili ile çalıştırılmaktadır.

---

## Geliştirme Ortamı

Yerel geliştirme için de Docker Compose kullanılır:

```bash
# Başlat
docker-compose up -d --build

# Web servis logları
docker-compose logs -f web

# Veritabanına bağlan
docker exec -it camasirhane_db psql -U <kullanici> <veritabani>

# Yalnızca web servisini yeniden başlat (kod değişikliklerinde)
docker-compose restart web
```

FastAPI'nin otomatik dokümantasyonu (Swagger UI / ReDoc) **varsayılan olarak kapalıdır**. `app = FastAPI(docs_url=os.getenv("DOCS_URL", None), redoc_url=os.getenv("REDOC_URL", None))` yapılandırması nedeniyle `/docs` ve `/redoc` yalnızca ilgili env değişkenleri açıkça set edildiğinde (ör. geliştirme ortamında `DOCS_URL=/docs`) erişilebilir. Üretimde bu değişkenler set edilmez.
