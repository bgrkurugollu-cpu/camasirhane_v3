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
| Kimlik Doğrulama | JWT (python-jose) + OAuth2PasswordBearer |
| Şifre Hashleme | bcrypt (passlib) |
| Rate Limiting | slowapi (IP bazlı) |
| Frontend | Vanilla JS + Tailwind CSS (CDN) + Chart.js |

### 3.2 API Endpoint Haritası

#### Auth
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| POST | `/api/token` | Herkese açık | Login → JWT token üretir (10 istek/dk limit) |
| GET | `/api/users/me` | user/admin | Kendi profil bilgisi |
| PUT | `/api/users/me` | user/admin | Profil güncelleme |
| POST | `/api/users/me/photo` | user/admin | Profil fotoğrafı yükleme (PNG) |

#### Kullanıcı Yönetimi (Admin)
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/users` | admin | Tüm kullanıcıları listele |
| POST | `/api/users` | admin | Yeni kullanıcı oluştur |
| PUT | `/api/users/{id}` | admin | Kullanıcı güncelle |
| DELETE | `/api/users/{id}` | admin | Kullanıcı sil |

#### Çalışan & RFID Eşleştirme
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/calisan/{sicil}` | user/admin | Sicil numarasına göre personel getir |
| POST | `/api/kiyafet` | admin | Yeni RFID–sicil eşleştirmesi ekle |
| PUT | `/api/kiyafet/{rfid}` | admin | RFID eşleştirmesini güncelle |
| DELETE | `/api/kiyafet/{rfid}` | admin | RFID eşleştirmesini sil |

#### İş Akışı / İşlemler
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| POST | `/api/islem/rfid-oku` | user/admin | Kirli sepet simülasyonu (rastgele 10 kıyafet ekler) |
| POST | `/api/islem` | user/admin | Manuel kirli / temiz / teslim kaydı oluştur (60 istek/dk) |
| POST | `/api/islem/onayla` | user/admin | Kirli kıyafeti "temiz" olarak işaretle, raf ata |
| POST | `/api/islem/teslim` | user/admin | Temiz kıyafeti personele teslim et |

#### İstatistik & Raporlama
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/stats` | user/admin | Günlük kirli/temiz/teslim sayıları |
| GET | `/api/stats/raflar` | user/admin | Tüm rafların doluluk durumu |
| GET | `/api/stats/raf-detay/{harf}` | user/admin | Belirli raftaki kıyafet detayları |
| GET | `/api/stats/history` | user/admin | Haftalık/aylık geçmiş grafik verisi |

#### Tablolar
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/tablo/kirli` | user/admin | Onay bekleyen kirli kıyafetler (son 50) |
| GET | `/api/tablo/temiz` | user/admin | Rafta bekleyen temiz kıyafetler (son 50) |
| GET | `/api/tablo/teslim` | admin | Tüm teslim geçmişi (son 50) |
| GET | `/api/tablo/kiyafet` | admin | RFID eşleştirme tablosu (server-side arama + sayfalama) |

#### Denetim
| Metod | Endpoint | Yetki | Açıklama |
|---|---|---|---|
| GET | `/api/audit-logs` | admin | Sistem audit logları (filtreli) |
| POST | `/api/init_mock_data` | admin | Test verisi oluşturma |

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
| Kimlik Doğrulama | JWT (HS256), `Authorization: Bearer <token>` |
| Token Süresi | 1440 dk (24 saat), `.env` ile yapılandırılabilir |
| Şifre Hashleme | bcrypt |
| Rate Limiting | `/api/token`: 10 istek/dk · `/api/islem`: 60 istek/dk (IP bazlı) |
| Yetkilendirme | Role-based: `admin` ve `user` |
| SSL/TLS | TLS 1.2/1.3, Nginx'te terminate edilir |
| Audit Log | Tüm giriş, çıkış ve işlem olayları `audit_logs` tablosuna yazılır |
| Proxy Desteği | `X-Forwarded-For` başlığından gerçek IP alınır |

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
| State | `localStorage` | JWT token saklanır |
| Auth Akışı | Token yoksa login modal gösterilir, tüm API istekleri `fetchWithAuth()` ile yapılır |

---

## 9. Yapılandırma (`.env`)

| Değişken | Açıklama |
|---|---|
| `SECRET_KEY` | JWT imzalama anahtarı (zorunlu) |
| `JWT_ALGORITHM` | HS256 (varsayılan) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 (varsayılan) |
| `POSTGRES_USER` | Veritabanı kullanıcı adı |
| `POSTGRES_PASSWORD` | Veritabanı şifresi |
| `POSTGRES_DB` | Veritabanı adı |
| `DATABASE_URL` | SQLAlchemy bağlantı dizesi |
| `TZ` | Zaman dilimi (Europe/Istanbul) |

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
│   ├── main.py              # FastAPI uygulama giriş noktası + tüm endpoint'ler
│   ├── models.py            # SQLAlchemy ORM modelleri
│   ├── schemas.py           # Pydantic istek/yanıt şemaları
│   ├── database.py          # DB bağlantısı ve session yönetimi
│   ├── security.py          # JWT, bcrypt, OAuth2 yardımcıları
│   └── static/
│       ├── index.html       # Tek sayfa uygulama (SPA)
│       ├── app.js           # Tüm frontend iş mantığı
│       ├── style.css        # Özel stiller
│       ├── logo.png         # Uygulama logosu
│       └── avatars/         # Profil fotoğrafları
└── docs/
    ├── topoloji.md          # Bu doküman
    └── ...
```
