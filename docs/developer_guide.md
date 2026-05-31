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
- JWT tokenlar `python-jose` ile oluşturulur ve doğrulanır.
- `SECRET_KEY`, `ALGORITHM` ve token geçerlilik süresi ortam değişkenlerinden okunur.
- `get_current_user` dependency'si tüm korumalı endpointlerde kullanılır.
- `require_role("admin")` ile rol bazlı erişim kontrolü uygulanır.

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

### Kimlik Doğrulama
| Metod | Yol | Açıklama | Rate Limit |
|---|---|---|---|
| POST | `/api/token` | Giriş; JWT döner | 10/dakika |
| POST | `/api/register` | Yeni kullanıcı kaydı | — |

### İşlem (Kıyafet Döngüsü)
| Metod | Yol | Açıklama | Rate Limit |
|---|---|---|---|
| POST | `/api/islem/kirli` | Kirli kıyafet girişi | 60/dakika |
| POST | `/api/islem/temizlendi` | Kıyafeti temizlendi olarak işaretle, raf ata | 60/dakika |
| POST | `/api/islem/teslim` | Kıyafeti teslim et | 60/dakika |
| GET | `/api/islem/rfid-oku` | Rastgele 10 personel için RFID simülasyonu | — |

### Tablo Listeleme
| Metod | Yol | Açıklama |
|---|---|---|
| GET | `/api/tablo/kirli` | Kirli kıyafetler (ad soyad JOIN) |
| GET | `/api/tablo/temiz` | Temiz kıyafetler (ad soyad JOIN) |
| GET | `/api/tablo/teslim` | Teslim edilecekler (ad soyad JOIN) |

### İstatistik ve Raf
| Metod | Yol | Açıklama |
|---|---|---|
| GET | `/api/stats/raflar` | Tüm rafların doluluk özeti |
| GET | `/api/stats/raf-detay/{harf}` | Belirli bir rafın tüm gözlerinin detayı |
| GET | `/api/stats/dashboard` | Dashboard istatistikleri |

### Yönetim (Admin)
| Metod | Yol | Açıklama |
|---|---|---|
| GET/POST | `/api/calisanlar` | Personel listesi / ekleme |
| GET/PUT/DELETE | `/api/calisanlar/{id}` | Personel güncelleme / silme |
| GET/POST | `/api/kiyafetler` | RFID demirbaş listesi / ekleme |
| GET | `/api/audit-log` | Denetim kaydı |

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
- **JWT RS256:** HMAC (HS256) yerine Asimetrik RS256 (Private/Public Key) şifrelemesi kullanılmaktadır.
- **CSRF ve Güvenlik Başlıkları:** `Double Submit Cookie` mantığı ile CSRF koruması aktiftir. `SecurityHeadersMiddleware` ile CSP, X-Frame-Options gibi başlıklar zorunlu kılınmıştır.
- **Rate Limiting:** `slowapi` ile IP başına istek sınırı (`/api/token`: 10/dk, `/api/islem/*`: 60/dk)
- **Hesap Kilitleme:** 5 hatalı şifre denemesinde hesap 15 dakika boyunca kilitlenir.
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

FastAPI'nin otomatik dokümantasyonu (Swagger UI) geliştirme amaçlı olarak `/docs` adresinde erişilebilir durumdadır. Üretim ortamında bu endpoint devre dışı bırakılmalıdır.
